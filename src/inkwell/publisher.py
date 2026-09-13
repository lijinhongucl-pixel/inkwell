"""发布模块：推送内容到目标平台

支持两种模式：
1. 微信公众号草稿箱 API（需要 access_token + app_id）
2. 剪贴板复制（自动提取 HTML 正文，复制到剪贴板，用户手动粘贴到公众号编辑器）

用法：
    publisher = Publisher()
    publisher.publish_to_clipboard(html_path)
    publisher.publish_to_wechat(html_path, access_token="...", title="文章标题")
"""

from __future__ import annotations

import base64
import html as html_lib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PublishResult:
    """发布结果"""

    success: bool
    platform: str  # clipboard / wechat
    message: str
    media_id: str = ""  # 微信返回的 media_id
    article_url: str = ""  # 微信文章 URL
    images_total: int = 0  # 正文里待转存的图片数
    images_transferred: int = 0  # 成功转存到微信图床的图片数
    warnings: list[str] = field(default_factory=list)


class Publisher:
    """内容发布器

    clipboard 模式无需任何凭证，适合个人手动粘贴。
    wechat 模式需要公众号 AppID + AppSecret 换取 access_token。
    """

    WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"

    # 微信 draft/add 的硬性上限（官方文档），超了会被接口拒绝，提前拦更友好
    TITLE_MAX = 32
    AUTHOR_MAX = 16
    DIGEST_MAX = 128
    CONTENT_MAX = 20000

    IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
    IMG_SRC_RE = re.compile(r"""\bsrc\s*=\s*("([^"]*)"|'([^']*)')""", re.IGNORECASE)

    def __init__(self) -> None:
        self.last_token_error = ""

    # ---------- 剪贴板模式 ----------
    def publish_to_clipboard(self, html_path: Path) -> PublishResult:
        """提取 HTML 正文，以「富文本」形式写入剪贴板，粘贴到公众号直接是排版后的效果

        关键：剪贴板必须带上 HTML flavor（macOS 的 «class HTML» /
        Linux 的 text/html target），只写纯文本会导致粘贴进公众号的是
        HTML 源码字面量而不是渲染结果。

        降级顺序：
          1. 平台专属富文本写入（macOS AppleScript / Linux xclip）
          2. 失败则回退纯文本写入，并明确告知用户改用手动复制
        """
        html = html_path.read_text(encoding="utf-8")
        # 提取 <section> 正文区域
        body = self._extract_section(html)
        if not body:
            body = html  # 降级：复制全文
        plain = self._strip_tags(body)

        # 1. 平台专属富文本写入
        try:
            if sys.platform == "darwin":
                self._copy_html_macos(body, plain)
                return PublishResult(
                    success=True,
                    platform="clipboard",
                    message="已以富文本写入剪贴板，打开公众号编辑器 ⌘+V 直接粘贴",
                )
            if sys.platform.startswith("linux"):
                self._copy_html_linux(body)
                return PublishResult(
                    success=True,
                    platform="clipboard",
                    message="已以富文本写入剪贴板，打开公众号编辑器 Ctrl+V 直接粘贴",
                )
        except Exception as e:
            # 落入下方纯文本降级
            fallback_reason = str(e)
        else:
            fallback_reason = f"当前平台（{sys.platform}）无内置富文本剪贴板支持"

        # 2. 纯文本降级
        ok, msg = self._copy_plain(plain)
        if ok:
            return PublishResult(
                success=True,
                platform="clipboard",
                message=(
                    f"已复制纯文本到剪贴板（{fallback_reason}）。"
                    "粘贴到公众号会得到无格式文字，需要排版效果请在浏览器打开 HTML 后手动全选复制。"
                ),
            )
        return PublishResult(
            success=False,
            platform="clipboard",
            message=msg,
        )

    # ---------- 剪贴板写入实现 ----------
    @staticmethod
    def _copy_html_macos(html: str, plain: str) -> None:
        """macOS：通过 AppleScript 同时写入 «class HTML» 与 string 两种 flavor

        路径以 argv 传入，避免拼接 AppleScript 源码时的引号转义问题。
        """
        if not shutil.which("osascript"):
            raise RuntimeError("未找到 osascript")
        d = Path(tempfile.mkdtemp(prefix="inkwell-cb-"))
        html_file = d / "body.html"
        text_file = d / "body.txt"
        html_file.write_text(html, encoding="utf-8")
        text_file.write_text(plain, encoding="utf-8")
        script = (
            "on run argv\n"
            "  set h to read (POSIX file (item 1 of argv)) as «class HTML»\n"
            "  set t to read (POSIX file (item 2 of argv)) as «class utf8»\n"
            "  set the clipboard to {«class HTML»:h, string:t}\n"
            "end run"
        )
        proc = subprocess.run(
            ["osascript", "-e", script, str(html_file), str(text_file)],
            capture_output=True,
            timeout=15,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="replace").strip())
        shutil.rmtree(d, ignore_errors=True)

    @staticmethod
    def _copy_html_linux(html: str) -> None:
        """Linux：xclip 支持指定 text/html target"""
        if not shutil.which("xclip"):
            raise RuntimeError("未找到 xclip（apt install xclip）")
        proc = subprocess.run(
            ["xclip", "-selection", "clipboard", "-t", "text/html"],
            input=html.encode("utf-8"),
            capture_output=True,
            timeout=10,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode("utf-8", errors="replace").strip())

    @staticmethod
    def _copy_plain(text: str) -> tuple[bool, str]:
        """纯文本写入（各平台兜底）"""
        cmd = Publisher._get_clipboard_command()
        if not cmd:
            return False, "未找到剪贴板命令（pbcopy/xclip/clip）"
        try:
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=5,
            )
            if proc.returncode == 0:
                return True, "已复制"
            return False, f"剪贴板写入失败: {proc.stderr.decode('utf-8', errors='replace')}"
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    # ---------- 微信公众号草稿箱 API ----------
    def publish_to_wechat(
        self,
        html_path: Path,
        title: str,
        thumb_media_id: str = "",
        author: str = "",
        digest: str = "",
        thumb_image: Path | None = None,
    ) -> PublishResult:
        """推送文章到公众号草稿箱

        需要先获取 access_token（通过 AppID + AppSecret）。
        环境变量 WECHAT_APP_ID + WECHAT_APP_SECRET 自动读取。

        微信侧实际有四道闸门，顺序不能错：
        1. 本地校验：标题/作者/摘要长度、封面来源（不通过就不发任何请求）
        2. 获取 access_token
        3. 封面：给了 thumb_image 就调 material/add_material 换成永久素材 media_id
        4. 正文图：逐张调 media/uploadimg 换成微信图床 URL（外链会被微信过滤掉）
        5. 新增草稿 → 返回 media_id
        """
        app_id = os.getenv("WECHAT_APP_ID", "")
        app_secret = os.getenv("WECHAT_APP_SECRET", "")

        # 1. 本地就能判定的问题先拦掉，不白花一次 token 调用
        if not app_id or not app_secret:
            return PublishResult(
                success=False,
                platform="wechat",
                message=("缺少 WECHAT_APP_ID 或 WECHAT_APP_SECRET 环境变量。请在公众号后台 → 开发 → 基本配置获取。"),
            )
        problem = self._validate_lengths(title, author, digest)
        if problem:
            return PublishResult(success=False, platform="wechat", message=problem)
        if not thumb_media_id and thumb_image is None:
            return PublishResult(
                success=False,
                platform="wechat",
                message=(
                    "缺少封面。公众号草稿接口要求封面为已上传的永久素材，"
                    "请用 --thumb-image <本地图片路径> 自动上传，或先用 --thumb 传入已有 media_id。"
                ),
            )

        # 2. 获取 access_token
        token = self._get_access_token(app_id, app_secret)
        if not token:
            detail = self.last_token_error or "检查 AppID/AppSecret 是否正确、调用方出口 IP 是否已加入白名单"
            return PublishResult(
                success=False,
                platform="wechat",
                message=f"获取 access_token 失败: {detail}",
            )

        warnings: list[str] = []

        # 3. 封面：本地图自动上传成永久素材
        if not thumb_media_id and thumb_image is not None:
            data, filename, ctype, why = self._load_image(str(thumb_image), None)
            if data is None:
                return PublishResult(
                    success=False,
                    platform="wechat",
                    message=f"封面图读取失败（{why}）: {thumb_image}",
                )
            url = f"{self.WECHAT_API_BASE}/material/add_material?type=image&access_token={token}"
            resp = self._post_multipart(url, "media", filename, data, ctype)
            thumb_media_id = resp.get("media_id", "")
            if not thumb_media_id:
                return PublishResult(
                    success=False,
                    platform="wechat",
                    message=f"封面上传失败: {self._api_error(resp) or '接口无响应'}",
                )

        # 4. 正文：提取 <section> 后把图逐张转存到微信图床
        html = html_path.read_text(encoding="utf-8")
        body = self._extract_section(html) or html
        body, images_total, images_transferred, img_warnings = self._transfer_images(body, html_path.parent, token)
        warnings.extend(img_warnings)
        if len(body) > self.CONTENT_MAX:
            warnings.append(f"正文 {len(body)} 字符，超过微信上限 {self.CONTENT_MAX}，接口可能直接拒绝")

        # 5. 新增草稿
        draft_url = f"{self.WECHAT_API_BASE}/draft/add?access_token={token}"
        article: dict = {
            "title": title,
            "author": author,
            "content": body,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        # digest 留空时微信会自己抓正文前 54 字，比塞标题更合适
        if digest:
            article["digest"] = digest
        payload = json.dumps({"articles": [article]}).encode("utf-8")
        req = urllib.request.Request(
            draft_url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        counts = {"images_total": images_total, "images_transferred": images_transferred, "warnings": warnings}
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception as e:  # noqa: BLE001
            return PublishResult(success=False, platform="wechat", message=f"调用草稿接口失败: {e}", **counts)
        if "media_id" not in data:
            return PublishResult(
                success=False,
                platform="wechat",
                message=f"API 返回错误: {self._api_error(data)}",
                **counts,
            )
        message = "草稿已推送到公众号草稿箱"
        if images_total:
            message += f"（正文图片 {images_transferred}/{images_total} 张已转存到微信图床）"
        return PublishResult(success=True, platform="wechat", message=message, media_id=data["media_id"], **counts)

    # ---------- 微信内部 ----------
    @staticmethod
    def _api_error(data: dict) -> str:
        """把微信的错误响应压成一行，便于 CLI 直接展示"""
        if not data:
            return ""
        return f"errcode={data.get('errcode')} errmsg={data.get('errmsg')}"

    @classmethod
    def _validate_lengths(cls, title: str, author: str, digest: str) -> str:
        """微信对这几个字段有硬性字数上限，超了会被拒 —— 本地先拦"""
        if not title:
            return "标题不能为空（微信草稿接口要求 title 必填）"
        if len(title) > cls.TITLE_MAX:
            return f"标题 {len(title)} 字，超过微信上限 {cls.TITLE_MAX} 字"
        if len(author) > cls.AUTHOR_MAX:
            return f"作者 {len(author)} 字，超过微信上限 {cls.AUTHOR_MAX} 字"
        if len(digest) > cls.DIGEST_MAX:
            return f"摘要 {len(digest)} 字，超过微信上限 {cls.DIGEST_MAX} 字"
        return ""

    @classmethod
    def _load_image(cls, src: str, base_dir: Path | None) -> tuple[bytes | None, str, str, str]:
        """按 src 取到图片字节并归一成微信接受的 jpg/png

        返回 (数据, 文件名, 内容类型, 失败原因)，失败时数据为 None。
        原因必须带出去 —— 只报「读取失败」分不清是 404、超时还是格式不对，
        而处理办法完全不同（换图床 / 加白名单 / 换格式）。

        支持三类 src：base64 内嵌、http(s) 外链、本地相对/绝对路径。
        """
        raw: bytes | None = None
        why = ""
        if src.startswith("data:"):
            b64 = src.partition(",")[2]
            try:
                raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
            except (ValueError, TypeError) as e:
                why = f"base64 解码失败: {e}"
        elif src.startswith(("http://", "https://")):
            try:
                req = urllib.request.Request(src, headers={"User-Agent": "inkwell"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    raw = resp.read()
            except Exception as e:  # noqa: BLE001
                why = f"下载失败 {type(e).__name__}: {e}"
        elif src:
            path = Path(src)
            if not path.is_absolute() and base_dir is not None:
                path = base_dir / src
            if not path.exists():
                why = f"文件不存在: {path}"
            else:
                try:
                    raw = path.read_bytes()
                except OSError as e:
                    why = f"读取失败: {e}"
        else:
            why = "src 为空"
        if not raw:
            return None, "", "", why or "内容为空"
        normalized = cls._normalize_image(raw)
        if normalized is None:
            return None, "", "", "格式不受支持（微信只收 jpg/png，转码也失败）"
        data, filename, ctype = normalized
        return data, filename, ctype, ""

    @staticmethod
    def _normalize_image(raw: bytes) -> tuple[bytes, str, str] | None:
        """微信 uploadimg 只吃 jpg/png：按魔术字节判断，必要时用 Pillow 转 JPEG"""
        if raw[:3] == b"\xff\xd8\xff":
            return raw, "image.jpg", "image/jpeg"
        if raw[:8] == b"\x89PNG\r\n\x1a\n":
            return raw, "image.png", "image/png"
        try:
            from PIL import Image

            with Image.open(io.BytesIO(raw)) as im:
                buf = io.BytesIO()
                im.convert("RGB").save(buf, format="JPEG", quality=88, optimize=True)
            return buf.getvalue(), "image.jpg", "image/jpeg"
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _post_multipart(url: str, field: str, filename: str, data: bytes, ctype: str) -> dict:
        """构造 multipart/form-data 上传（手写，不引入额外依赖）"""
        boundary = f"----inkwell{uuid.uuid4().hex}"
        head = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n"
        ).encode()
        body = head + data + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception:  # noqa: BLE001
            return {}

    def _transfer_images(self, content: str, base_dir: Path | None, token: str) -> tuple[str, int, int, list[str]]:
        """把正文里的图片逐张转存到微信图床，并把 src 换成 mmbiz 地址

        微信 draft/add 会**过滤外链图**（含 data: 内嵌），所以必须先用
        media/uploadimg 换成微信自己的地址。单张失败只记告警，不阻断推送。
        """
        total = 0
        ok = 0
        warnings: list[str] = []

        def repl(match: re.Match) -> str:
            nonlocal total, ok
            tag = match.group(0)
            sm = self.IMG_SRC_RE.search(tag)
            if sm is None:
                return tag
            src = sm.group(2) if sm.group(2) is not None else sm.group(3)
            if not src or "mmbiz.qpic.cn" in src:
                return tag  # 本来就是微信图床，跳过
            total += 1
            data, filename, ctype, why = self._load_image(src, base_dir)
            if data is None:
                warnings.append(f"第 {total} 张图片转存失败（{why}），草稿里这张图会缺失: {src[:60]}")
                return tag
            url = f"{self.WECHAT_API_BASE}/media/uploadimg?access_token={token}"
            resp = self._post_multipart(url, "media", filename, data, ctype)
            new_src = resp.get("url", "")
            if not new_src:
                warnings.append(
                    f"第 {total} 张图片转存失败: {self._api_error(resp) or '接口无响应'}，草稿里这张图会缺失"
                )
                return tag
            ok += 1
            return tag.replace(sm.group(0), f'src="{new_src}"')

        return self.IMG_TAG_RE.sub(repl, content), total, ok, warnings

    def _get_access_token(self, app_id: str, app_secret: str) -> str:
        """通过 AppID + AppSecret 换取 access_token"""
        url = f"{self.WECHAT_API_BASE}/token?" + urllib.parse.urlencode(
            {
                "grant_type": "client_credential",
                "appid": app_id,
                "secret": app_secret,
            }
        )
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            if "access_token" in data:
                return data["access_token"]
            # 典型场景：errcode 40164 —— 出口 IP 不在白名单，把原文留给用户看
            self.last_token_error = self._api_error(data)
            return ""
        except Exception as e:  # noqa: BLE001
            self.last_token_error = str(e)
            return ""

    @staticmethod
    def _extract_section(html: str) -> str:
        """提取最外层 <section>...</section>（去除 DOCTYPE/html/head/body 外壳）

        用深度配对而不是非贪婪正则：正文里可能嵌套 <section>
        （目录卡片、图片卡片等），非贪婪正则会停在第一个 </section> 上把正文截断。
        """
        m = re.search(r"<section[^>]*>", html, re.I)
        if not m:
            return ""
        start = m.start()
        depth = 0
        for tag in re.finditer(r"<section[^>]*>|</section\s*>", html[start:], re.I):
            if tag.group(0).startswith("</"):
                depth -= 1
                if depth == 0:
                    return html[start : start + tag.end()]
            else:
                depth += 1
        return html[start:]  # 标签不闭合时返回剩余部分

    @staticmethod
    def _strip_tags(html: str) -> str:
        """把 HTML 压成纯文本，供剪贴板的纯文本 flavor 使用"""
        # 块级标签与 <br> 转成换行，避免文字黏连
        text = re.sub(
            r"</(?:p|div|section|h[1-6]|li|tr|table|blockquote)\s*>|<br\s*/?>",
            "\n",
            html,
            flags=re.I,
        )
        text = re.sub(r"<[^>]+>", "", text)
        text = html_lib.unescape(text)
        # 去空行、行首尾空白
        lines = [ln.strip() for ln in text.splitlines()]
        return "\n".join(ln for ln in lines if ln)

    @staticmethod
    def _get_clipboard_command() -> list[str] | None:
        """检测系统剪贴板命令（纯文本兜底用）"""
        for cmd in ["pbcopy", "xclip", "clip"]:
            if shutil.which(cmd):
                return [cmd]
        return None
