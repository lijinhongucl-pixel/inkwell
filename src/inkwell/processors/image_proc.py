"""图片处理：压缩 + CDN 上传 + base64 本地预览版

严格遵循用户记忆中的坑：
- PIL 压缩参数：RGB 去alpha、600宽 LANCZOS、JPEG quality=82 optimize
- GitHub Contents API 上传（不走 git push），token 从环境变量或参数传入
- base64 本地版只做 IDE 预览，发布版用 CDN 外链
- 整段替换 src，不要正则保留前缀

本地预览版的双轨必须覆盖「输入本来就是外链图」的情况：
正文图常常直接写成 https://cdn.jsdelivr.net/... 这种外链（用户自己的图床），
若对 http(s) 一律原样返回，_local_map 里就没有记录，to_local_preview()
替换不到任何东西 —— 两个版本字节完全相同，IDE 预览面板加载不了外网时全裂图。
所以外链图也要下载下来压缩成 base64 放进 map（发布版仍保留原外链）。
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
    EXTERNAL_PREFIXES = ("http://", "https://")
    # 部分 CDN（GitHub raw 等）无 UA 会 403
    USER_AGENT = "inkwell/0.8 (+https://github.com/lijinhongucl-pixel/inkwell)"
    # 默认下载上限 5 MB：防超大图拖慢流水线
    DEFAULT_MAX_DOWNLOAD = 5 * 1024 * 1024

    def __init__(
        self,
        quality: int = 82,
        max_width: int = 600,
        cdn_base: str = "",
        github_token: str | None = None,
        github_repo: str = "",
        image_subdir: str = "",
        embed_external: bool = True,
        max_download_bytes: int = DEFAULT_MAX_DOWNLOAD,
        download_timeout: float = 15.0,
    ) -> None:
        self.quality = quality
        self.max_width = max_width
        self.cdn_base = cdn_base.rstrip("/")
        self.token = github_token or os.getenv("GITHUB_TOKEN")
        self.repo = github_repo
        self.subdir = image_subdir.strip("/")
        # 外链图是否下载内嵌进本地预览版（发布版始终保留原外链）
        self.embed_external = embed_external
        self.max_download_bytes = max_download_bytes
        self.download_timeout = download_timeout
        # CDN 外链 → base64 的映射，供本地预览版整段替换
        self._local_map: dict[str, str] = {}
        # 处理过程中的非致命问题（图片缺失 / 压缩失败 / 上传失败）
        self.warnings: list[str] = []
        # 成功内嵌进本地预览版的外链图
        self.embedded_external: list[str] = []

    # ---------- 对外接口 ----------
    def process_html(self, html: str, base_dir: Path) -> tuple[str, list[str]]:
        """扫描 HTML 中的图片，压缩 + 上传，替换为 CDN URL

        上传不可用时自动降级为 base64 内嵌，绝不因为单张图失败而中断整条流水线。
        返回 (新 HTML, 图片引用列表) —— 列表里可能是 CDN URL、data URI，
        或「本来就是外链、原样保留」的 http(s) 地址。

        外链图（http/https）：发布版保留原地址（公众号粘贴时会自己转存），
        同时下载压缩后记入 _local_map，供本地预览版内嵌。
        """
        uploads: list[str] = []
        self._local_map.clear()
        self.warnings.clear()
        self.embedded_external.clear()
        skipped_external = 0

        # CDN 三项（token / repo / cdn_base）必须齐备。若只给 token+repo 而缺
        # cdn_base，_upload 会返回 "/path" 这种畸形相对地址，粘进公众号图全裂 ——
        # 所以此处直接判定为不可用。只预告警一次，避免逐图重复刷屏。
        if self.token and self.repo and not self.cdn_base:
            self._warn(
                "已提供 GITHUB_TOKEN 与 github_repo，但缺少 cdn_base，无法生成可访问的图片外链，已降级为内嵌 base64"
            )

        def repl(m: re.Match) -> str:
            nonlocal skipped_external
            prefix, src, suffix = m.group(1), m.group(2), m.group(3)

            if src.startswith("data:"):
                # base64 内嵌图在公众号正文会被过滤，发布版不该出现
                self._warn("正文含 data:image base64 内嵌图，公众号编辑器会过滤掉这类图片，建议改用 CDN 外链")
                return m.group(0)

            if src.startswith(self.EXTERNAL_PREFIXES):
                uploads.append(src)
                if not self.embed_external:
                    skipped_external += 1
                    return m.group(0)
                data_uri = self._embed_external(src)
                if data_uri:
                    # 发布版保留原外链；本地预览版替换成 base64
                    self._local_map[src] = data_uri
                    self.embedded_external.append(src)
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

        if skipped_external:
            self._warn(
                f"已跳过 {skipped_external} 张外链图的内嵌（--no-embed-external），"
                "本地预览版会继续用外链，离线打开时会裂图"
            )
        return new_html, uploads

    def to_local_preview(self, html: str) -> str:
        """把发布版 HTML 里的图片外链整段替换回 base64 data URI

        用途：IDE 预览面板 / 离线打开时加载不了外网 CDN，需要内嵌图。
        映射里既有我们上传后生成的 CDN 链，也有正文里本来就是外链的图。

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
    def _embed_external(self, src: str) -> str | None:
        """下载外链图 → 压缩 → base64；失败返回 None 并记告警

        只服务于本地预览版：发布版仍保留原外链（公众号粘贴外链图时会自己转存）。
        任何失败都不阻断流水线，但告警必须带具体原因，便于定位（曾因为只报
        「读取失败」白排查一轮）。
        """
        try:
            raw = self._download_bytes(src)
        except Exception as e:  # noqa: BLE001
            self._warn(f"外链图下载失败，本地预览版仍是外链（离线会裂图）: {src}（{e}）")
            return None
        if len(raw) > self.max_download_bytes:
            self._warn(f"外链图超过 {self.max_download_bytes // 1024} KB 上限，已跳过内嵌: {src}")
            return None
        try:
            return self._to_data_uri(self._compress_bytes(raw))
        except Exception as e:  # noqa: BLE001
            self._warn(f"外链图解码失败，已跳过内嵌: {src}（{e}）")
            return None

    def _download_bytes(self, url: str) -> bytes:
        """下载外链图，最多读 max_download_bytes + 1 字节用来判超限"""
        req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.download_timeout) as resp:
            return resp.read(self.max_download_bytes + 1)

    def _compress(self, src_path: Path) -> bytes:
        """PIL 压缩：RGB → 600宽 LANCZOS → JPEG q82 optimize"""
        return self._compress_bytes(src_path.read_bytes())

    def _compress_bytes(self, data: bytes) -> bytes:
        """同 _compress，但输入是内存里的图片字节（外链图走这条）"""
        img = Image.open(io.BytesIO(data))
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
