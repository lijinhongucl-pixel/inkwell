"""图片处理：压缩 + CDN 上传 + base64 本地预览版

严格遵循用户记忆中的坑：
- PIL 压缩参数：RGB 去alpha、600宽 LANCZOS、JPEG quality=82 optimize
- GitHub Contents API 上传（不走 git push），token 从环境变量或参数传入
- base64 本地版只做 IDE 预览，发布版用 CDN 外链
- 整段替换 src，不要正则保留前缀
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import urllib.request
from pathlib import Path

from PIL import Image


class ImageProcessor:
    # 只匹配 <img> 的 src，避免误伤 <script src> / <link href>
    IMG_SRC_RE = re.compile(r'(<img\b[^>]*?\bsrc=")([^"]+)(")', re.I)

    def __init__(
        self,
        quality: int = 82,
        max_width: int = 600,
        cdn_base: str = "",
        github_token: str | None = None,
        github_repo: str = "",
        image_subdir: str = "",
    ) -> None:
        self.quality = quality
        self.max_width = max_width
        self.cdn_base = cdn_base.rstrip("/")
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.repo = github_repo
        self.subdir = image_subdir.strip("/")
        # CDN 外链 → base64 的映射，供本地预览版整段替换
        self._local_map: dict[str, str] = {}
        # 处理过程中的非致命问题（图片缺失 / 压缩失败 / 上传失败）
        self.warnings: list[str] = []

    # ---------- 对外接口 ----------
    def process_html(self, html: str, base_dir: Path) -> tuple[str, list[str]]:
        """扫描 HTML 中的本地图片，压缩 + 上传，替换为 CDN URL

        上传不可用时自动降级为 base64 内嵌，绝不因为单张图失败而中断整条流水线。
        返回 (新 HTML, 图片引用列表) —— 列表里可能是 CDN URL 也可能是 data URI。
        """
        uploads: list[str] = []
        self._local_map.clear()
        self.warnings.clear()

        # CDN 三项（token / repo / cdn_base）必须齐备。若只给 token+repo 而缺
        # cdn_base，_upload 会返回 "/path" 这种畸形相对地址，粘进公众号图全裂 ——
        # 所以此处直接判定为不可用。只预告警一次，避免逐图重复刷屏。
        if self.token and self.repo and not self.cdn_base:
            self._warn(
                "已提供 GITHUB_TOKEN 与 github_repo，但缺少 cdn_base，无法生成可访问的图片外链，已降级为内嵌 base64"
            )

        def repl(m: re.Match) -> str:
            prefix, src, suffix = m.group(1), m.group(2), m.group(3)
            if src.startswith(("http://", "https://", "data:")):
                return m.group(0)
            local = (base_dir / src).resolve()
            if not local.exists():
                self._warn(f"图片不存在，已跳过: {src}")
                return m.group(0)
            try:
                compressed = self._compress(local)
            except Exception as e:  # noqa: BLE001
                self._warn(f"图片压缩失败，已跳过: {src}（{e}）")
                return m.group(0)

            data_uri = self._to_data_uri(compressed)

            if self.token and self.repo and self.cdn_base:
                try:
                    cdn_url = self._upload(compressed, local.name)
                except Exception as e:  # noqa: BLE001
                    self._warn(f"CDN 上传失败，已降级为内嵌图: {local.name}（{e}）")
                    uploads.append(data_uri)
                    return f"{prefix}{data_uri}{suffix}"
                uploads.append(cdn_url)
                # 记录映射：本地预览版需要把 CDN 链换回 base64
                self._local_map[cdn_url] = data_uri
                return f"{prefix}{cdn_url}{suffix}"

            # 无 token：直接内嵌 base64（降级）
            uploads.append(data_uri)
            return f"{prefix}{data_uri}{suffix}"

        new_html = self.IMG_SRC_RE.sub(repl, html)
        return new_html, uploads

    def to_local_preview(self, html: str) -> str:
        """把发布版 HTML 里的 CDN 外链整段替换回 base64 data URI

        用途：IDE 预览面板 / 离线打开时加载不了外网 CDN，需要内嵌图。

        关键坑：必须**整段替换** `src="cdn"` → `src="data:..."`。
        不要用正则保留 URL 前缀再拼 base64，否则会残留
        `...@main/dir/data:image/png;base64,...` 导致图片全裂。
        """
        for cdn_url, data_uri in self._local_map.items():
            html = html.replace(f'src="{cdn_url}"', f'src="{data_uri}"')
        return html

    def _warn(self, msg: str) -> None:
        self.warnings.append(msg)

    # ---------- 内部 ----------
    def _compress(self, src_path: Path) -> bytes:
        """PIL 压缩：RGB → 600宽 LANCZOS → JPEG q82 optimize"""
        img = Image.open(src_path)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        if img.width > self.max_width:
            ratio = self.max_width / img.width
            img = img.resize((self.max_width, int(img.height * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self.quality, optimize=True)
        return buf.getvalue()

    def _to_data_uri(self, data: bytes) -> str:
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"

    def _upload(self, data: bytes, filename: str) -> str:
        """通过 GitHub Contents API 上传，返回 CDN URL

        用户记忆：不要用 git push（中国网络 502），用 Contents API。
        不要走 curl 命令行（超长参数会挂），用 urllib。
        """
        path = f"{self.subdir}/{filename}" if self.subdir else filename
        url = f"https://api.github.com/repos/{self.repo}/contents/{path}"
        b64 = base64.b64encode(data).decode("ascii")
        payload = json.dumps({"message": f"upload {filename}", "content": b64}).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            method="PUT",
            headers={
                "Authorization": f"token {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req) as resp:
            resp.read()  # 确保完成
        return f"{self.cdn_base}/{path}"
