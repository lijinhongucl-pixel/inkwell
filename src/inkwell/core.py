"""流水线核心编排

Pipeline 负责把三个 processor 串起来：
    1. MarkdownProcessor  —— md → 带内联样式的 HTML 骨架
    2. ImageProcessor     —— 截图压缩 + base64/CDN 双版本
    3. CopyCompatValidator—— 公众号剪贴板兼容性静态扫描（flex/grid/inline-block 圆点）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .processors.image_proc import ImageProcessor
from .processors.markdown_proc import MarkdownProcessor
from .processors.validator import CopyCompatValidator


@dataclass
class PipelineConfig:
    """单次运行配置"""

    input_md: Path
    output_dir: Path
    theme: str = "moyu-green"  # 默认主题
    image_quality: int = 82
    image_max_width: int = 600
    # CDN 配置由用户自行填写（脱敏：不含任何默认仓库地址）
    cdn_base: str = ""  # 例：https://cdn.example.com/images
    github_token: str | None = None  # 无 token 时跳过上传，降级 base64
    github_repo: str = ""  # 例：your-org/your-image-repo
    image_subdir: str = ""  # CDN 子目录
    emit_local_preview: bool = True  # 同时生成 base64 本地预览版
    strict_copy_compat: bool = True  # 严格校验公众号兼容性


@dataclass
class PipelineResult:
    publish_html: Path | None = None
    local_html: Path | None = None
    uploaded_images: list[str] = field(default_factory=list)
    compat_warnings: list[str] = field(default_factory=list)
    image_warnings: list[str] = field(default_factory=list)


class Pipeline:
    """内容发布流水线入口"""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.md_proc = MarkdownProcessor(theme=config.theme)
        self.img_proc = ImageProcessor(
            quality=config.image_quality,
            max_width=config.image_max_width,
            cdn_base=config.cdn_base,
            github_token=config.github_token,
            github_repo=config.github_repo,
            image_subdir=config.image_subdir,
        )
        self.validator = CopyCompatValidator() if config.strict_copy_compat else None

    def run(self) -> PipelineResult:
        """执行流水线，返回产物路径"""
        result = PipelineResult()
        md_text = self.config.input_md.read_text(encoding="utf-8")

        # 1. Markdown → HTML 骨架
        html = self.md_proc.convert(md_text)

        # 2. 处理图片：上传 + 替换为 CDN URL（失败自动降级为内嵌 base64）
        html, uploads = self.img_proc.process_html(html, base_dir=self.config.input_md.parent)
        result.uploaded_images = uploads
        result.image_warnings = list(self.img_proc.warnings)

        # 3. 生成发布版（CDN 外链）
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        publish_path = self.config.output_dir / f"{self.config.input_md.stem}_预览.html"
        publish_path.write_text(html, encoding="utf-8")
        result.publish_html = publish_path

        # 4. 可选：生成 base64 本地预览版
        if self.config.emit_local_preview:
            local_html = self.img_proc.to_local_preview(html)
            local_path = self.config.output_dir / f"{self.config.input_md.stem}_预览_本地版.html"
            local_path.write_text(local_html, encoding="utf-8")
            result.local_html = local_path

        # 5. 公众号兼容性静态扫描
        if self.validator:
            warnings = self.validator.scan(publish_path)
            result.compat_warnings = warnings

        return result
