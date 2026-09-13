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

import html as html_lib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PublishResult:
    """发布结果"""

    success: bool
    platform: str  # clipboard / wechat
    message: str
    media_id: str = ""  # 微信返回的 media_id
    article_url: str = ""  # 微信文章 URL


class Publisher:
    """内容发布器

    clipboard 模式无需任何凭证，适合个人手动粘贴。
    wechat 模式需要公众号 AppID + AppSecret 换取 access_token。
    """

    WECHAT_API_BASE = "https://api.weixin.qq.com/cgi-bin"

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
    ) -> PublishResult:
        """推送文章到公众号草稿箱

        需要先获取 access_token（通过 AppID + AppSecret）。
        环境变量 WECHAT_APP_ID + WECHAT_APP_SECRET 自动读取。

        流程：
        1. 获取 access_token
        2. 上传封面图（如有 thumb_media_id 跳过）
        3. 新增草稿 → 返回 media_id
        """
        app_id = os.getenv("WECHAT_APP_ID", "")
        app_secret = os.getenv("WECHAT_APP_SECRET", "")

        if not app_id or not app_secret:
            return PublishResult(
                success=False,
                platform="wechat",
                message=("缺少 WECHAT_APP_ID 或 WECHAT_APP_SECRET 环境变量。请在公众号后台 → 开发 → 基本配置获取。"),
            )

        # 1. 获取 access_token
        token = self._get_access_token(app_id, app_secret)
        if not token:
            return PublishResult(
                success=False,
                platform="wechat",
                message="获取 access_token 失败，请检查 AppID/AppSecret",
            )

        # 2. 读取 HTML 内容
        html = html_path.read_text(encoding="utf-8")
        body = self._extract_section(html) or html

        # 3. 校验必需参数：微信草稿接口要求 thumb_media_id 是已上传素材的
        #    media_id，传占位字符串会被拒（errcode 40007），不如提前报错
        if not thumb_media_id:
            return PublishResult(
                success=False,
                platform="wechat",
                message=(
                    "缺少 --thumb（封面图 media_id）。公众号草稿接口要求封面为"
                    "已上传的永久素材，请先在公众号后台或素材接口上传封面图后传入。"
                ),
            )

        # 4. 新增草稿
        draft_url = f"{self.WECHAT_API_BASE}/draft/add?access_token={token}"
        article = {
            "title": title,
            "author": author,
            "digest": digest or title,
            "content": body,
            "thumb_media_id": thumb_media_id,
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        payload = json.dumps({"articles": [article]}).encode("utf-8")
        req = urllib.request.Request(
            draft_url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            if "media_id" in data:
                return PublishResult(
                    success=True,
                    platform="wechat",
                    message="草稿已推送到公众号草稿箱",
                    media_id=data["media_id"],
                )
            return PublishResult(
                success=False,
                platform="wechat",
                message=(f"API 返回错误: errcode={data.get('errcode')} errmsg={data.get('errmsg')}"),
            )
        except Exception as e:  # noqa: BLE001
            return PublishResult(success=False, platform="wechat", message=str(e))

    # ---------- 内部 ----------
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
            return data.get("access_token", "")
        except Exception:
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
