"""Markdown → 公众号兼容 HTML

严格遵守公众号剪贴板兼容铁律：
- 严禁 display:flex / grid / inline-block 自制图形
- 用 <table> + <td width> 做并排布局
- 圆点用 ● 字符，箭头用 →，分割线用 ———
- 所有样式内联，且文字节点一律包进 <span leaf="">（公众号只认 leaf 里的样式）
- 中文只用「」引号

内置 15 套排版主题，每套主题有独立色板和字体栈，共用同一套转换逻辑。
"""

from __future__ import annotations

import re
import textwrap

from .themes import THEMES, THEME_META

# 主题色板已抽出至 themes.py，此处仅保留导入。

TEMPLATE_HEAD = textwrap.dedent("""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:{bg};">
<section style="max-width:640px;margin:0 auto;padding:32px 20px 48px;font-family:{font};color:{text};font-size:16px;line-height:1.8;background-color:{bg};">
""")

TEMPLATE_TAIL = textwrap.dedent("""\
</section>
</body>
</html>
""")


class MarkdownProcessor:
    """把 Markdown 转成公众号剪贴板兼容的内联样式 HTML

    支持 15 套主题，切换主题只改变色板和字体，转换逻辑完全共用。
    """

    # ---------- <span leaf=""> 包裹 ----------
    # 公众号编辑器粘贴后，只有落在 <span leaf=""> 里的文字才会保留内联样式；
    # 正文一个 leaf 都没有 → 粘贴后样式大面积丢失（gzh-design 的
    # validate_gzh_html.py 把这判为 ERROR）。所以生成后统一补包一层。
    _TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
    _TAG_NAME_RE = re.compile(r"</?\s*([a-zA-Z][\w-]*)")
    _LEAF_TAG_RE = re.compile(r"<span\b[^>]*\bleaf\b", re.I)
    # 这些区域里的文字不属于公众号正文，不能包（包进 <title> 还是非法 HTML）
    _NO_LEAF_TAGS = frozenset({"style", "script", "title", "head"})

    def __init__(self, theme: str = "moyu-green") -> None:
        if theme not in THEMES:
            available = [t["id"] for t in THEME_META]
            raise ValueError(f"未知主题: {theme}，可选: {available}")
        self.theme_name = theme
        self.c = THEMES[theme]
        # 暗色背景主题自动适配辅助底色
        self._is_dark = self._is_dark_bg(self.c["bg"])
        self._quote_bg = "#2A2A3A" if self._is_dark else self._mix(self.c["bg"], self.c["primary"], 0.06)
        self._table_bg = self.c["bg"] if self._is_dark else self._mix(self.c["bg"], "#FFFFFF", 0.5)
        self._table_border = "#3A3A4A" if self._is_dark else self._mix(self.c["bg"], self.c["primary"], 0.2)
        self._inline_code_bg = "#2A2A3A" if self._is_dark else self._mix(self.c["bg"], self.c["primary"], 0.08)
        self._code_bg = "#000000" if self._is_dark else "#1E1E1E"

    @staticmethod
    def _mix(hex_a: str, hex_b: str, ratio: float) -> str:
        """混合两个十六进制颜色，ratio 偏向 b（0.0=纯 a，1.0=纯 b）"""

        def parse(h: str) -> tuple[int, int, int]:
            h = h.lstrip("#")
            if len(h) != 6:
                return (128, 128, 128)
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

        ra, ga, ba = parse(hex_a)
        rb, gb, bb = parse(hex_b)
        r = round(ra + (rb - ra) * ratio)
        g = round(ga + (gb - ga) * ratio)
        b = round(ba + (bb - ba) * ratio)
        return f"#{r:02X}{g:02X}{b:02X}"

    @staticmethod
    def _is_dark_bg(hex_color: str) -> bool:
        """判断是否暗色背景（亮度 < 0.5 视为暗色）"""
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return False
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        brightness = (r * 299 + g * 587 + b * 114) / 1000 / 255
        return brightness < 0.5

    # ---------- 公开入口 ----------
    def convert(self, md_text: str) -> str:
        """Markdown 字符串 → 完整 HTML 文件字符串"""
        body = self._md_to_inline_html(md_text)
        # 正文文字节点统一包 <span leaf="">，保证粘贴到公众号后样式不丢
        body = self._wrap_leaf(body)
        title = self._extract_title(md_text)
        head = TEMPLATE_HEAD.format(title=title, **self.c)
        return head + body + TEMPLATE_TAIL

    @classmethod
    def _wrap_leaf(cls, html: str) -> str:
        """给正文里的每个文本节点包一层 ``<span leaf="">``

        为什么必须包：公众号编辑器的粘贴逻辑只保留 ``<span leaf="">`` 内的文字样式，
        未包裹的文字会掉成默认样式。gzh-design 的 ``validate_gzh_html.py``
        直接把这判为 ERROR（「全文没有任何 <span leaf=""> 包裹」）。

        实现要点：按标签切分字符串，只替换文本片段 —— 标签与属性原样透传，
        不会重排属性顺序、不会改写引号（历史上引号替换曾把 ``style=""`` 变成 ``style=「」``）。
        ``<style>/<script>/<title>/<head>`` 内的文本不包；已经是 leaf 的不重复包。
        """
        parts = cls._TAG_SPLIT_RE.split(html)
        out: list[str] = []
        skip_depth = 0  # 处于 style/script/title/head 内
        leaf_depth = 0  # 处于既有 span leaf 内
        for part in parts:
            if not part:
                continue
            if part.startswith("<") and part.endswith(">"):
                out.append(part)
                m = cls._TAG_NAME_RE.match(part)
                if not m:
                    continue
                tag = m.group(1).lower()
                if part.startswith("</"):
                    if tag in cls._NO_LEAF_TAGS and skip_depth:
                        skip_depth -= 1
                    if tag == "span" and leaf_depth:
                        leaf_depth -= 1
                elif not part.endswith("/>"):
                    if tag in cls._NO_LEAF_TAGS:
                        skip_depth += 1
                    elif tag == "span" and cls._LEAF_TAG_RE.match(part):
                        leaf_depth += 1
                continue
            if skip_depth or leaf_depth or not part.strip():
                out.append(part)
                continue
            out.append(f'<span leaf="">{part}</span>')
        return "".join(out)

    @staticmethod
    def list_themes() -> list[dict[str, str]]:
        """返回所有可用主题列表"""
        return THEME_META.copy()

    # ---------- 核心：逐行转内联 HTML ----------
    def _md_to_inline_html(self, md: str) -> str:
        lines = md.splitlines()
        out: list[str] = []
        in_code = False
        in_comment = False
        code_buf: list[str] = []
        in_table = False
        table_rows: list[list[str]] = []

        for raw in lines:
            line = raw.rstrip()

            # --- 代码块 ---
            if line.startswith("```"):
                if in_code:
                    out.append(self._render_code("\n".join(code_buf)))
                    code_buf.clear()
                    in_code = False
                else:
                    in_code = True
                continue
            if in_code:
                code_buf.append(raw)
                continue

            # --- HTML 注释（草稿占位符 <!-- TODO: ... -->）---
            # 注释在 Markdown 里不应渲染成可见文字，整段剥掉；
            # 若一行里既有注释又有正文，只去掉注释部分
            if in_comment:
                if "-->" in line:
                    in_comment = False
                    line = line.split("-->", 1)[1].rstrip()
                    if not line.strip():
                        continue
                else:
                    continue
            if "<!--" in line:
                if "-->" in line:
                    line = re.sub(r"<!--.*?-->", "", line).rstrip()
                    if not line.strip():
                        continue
                else:
                    in_comment = True
                    line = line.split("<!--", 1)[0].rstrip()
                    if not line.strip():
                        continue

            # --- 表格 ---
            if line.startswith("|") and line.endswith("|"):
                if not in_table:
                    in_table = True
                    table_rows.clear()
                if re.match(r"^\|[\s:|-]+\|$", line):
                    continue
                cells = [c.strip() for c in line.strip("|").split("|")]
                table_rows.append(cells)
                continue
            else:
                if in_table:
                    out.append(self._render_table(table_rows))
                    table_rows.clear()
                    in_table = False

            # --- 空行 ---
            if not line.strip():
                # 不插入显式空白段，用下一段的 margin-top 自然控制间距
                continue

            # --- 标题 h1-h4 ---
            m = re.match(r"^(#{1,4})\s+(.*)", line)
            if m:
                level = len(m.group(1))
                text = self._inline(m.group(2))
                out.append(self._render_heading(level, text))
                continue

            # --- 分割线 ---
            if re.match(r"^(-{3,}|\*{3,}|_{3,})$", line):
                out.append(
                    f'<p style="text-align:center;color:{self.c["accent"]};'
                    f'font-size:14px;margin:32px 0;letter-spacing:8px;">———</p>'
                )
                continue

            # --- 引用 ---
            if line.startswith("> "):
                text = self._inline(line[2:])
                out.append(
                    f'<p style="border-left:3px solid {self.c["primary"]};'
                    f"padding:12px 18px;margin:20px 0;color:{self.c['text']};"
                    f"background-color:{self._quote_bg};border-radius:0 6px 6px 0;"
                    f'line-height:1.8;">{text}</p>'
                )
                continue

            # --- 无序列表 ---
            m = re.match(r"^\s*[-*]\s+(.*)", line)
            if m:
                text = self._inline(m.group(1))
                out.append(
                    f'<p style="margin:10px 0;padding-left:4px;line-height:1.75;">'
                    f'<span style="color:{self.c["primary"]};margin-right:10px;">●</span>'
                    f"<span>{text}</span></p>"
                )
                continue

            # --- 有序列表 ---
            m = re.match(r"^\s*(\d+)\.\s+(.*)", line)
            if m:
                num, text = m.group(1), self._inline(m.group(2))
                out.append(
                    f'<p style="margin:10px 0;padding-left:4px;line-height:1.75;">'
                    f'<span style="color:{self.c["primary"]};font-weight:bold;margin-right:10px;">{num}.</span>'
                    f"<span>{text}</span></p>"
                )
                continue

            # --- 图片 ---
            m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if m:
                alt, src = m.group(1), m.group(2)
                out.append(self._render_image(alt, src))
                continue

            # --- 普通段落 ---
            text = self._inline(line)
            out.append(f'<p style="margin:16px 0;color:{self.c["text"]};line-height:1.8;">{text}</p>')

        if in_table:
            out.append(self._render_table(table_rows))
        return "\n".join(out)

    # ---------- 内联标记 ----------
    def _inline(self, text: str) -> str:
        # 英文直引号 → 中文「」
        # ⚠️ 必须在生成 HTML 标签之前处理，否则会把 style="..." 里的
        #    双引号也替换成「，导致 HTML 属性完全崩溃
        if '"' in text:
            chars = list(text)
            quote_count = 0
            for i, ch in enumerate(chars):
                if ch == '"':
                    chars[i] = "「" if quote_count % 2 == 0 else "」"
                    quote_count += 1
            text = "".join(chars)

        # 粗体 **text** → 主色加粗
        text = re.sub(
            r"\*\*([^*]+)\*\*",
            rf'<strong style="color:{self.c["primary"]};font-weight:bold;">\1</strong>',
            text,
        )
        # 斜体 *text* → 高亮色
        text = re.sub(
            r"(?<!\*)\*([^*]+)\*(?!\*)",
            rf'<em style="color:{self.c["highlight"]};">\1</em>',
            text,
        )
        # ==高亮== → 下划线标记
        text = re.sub(
            r"==([^=]+)==",
            rf'<span style="border-bottom:2px solid {self.c["underline"]};font-weight:600;">\1</span>',
            text,
        )
        # 行内代码
        code_bg = self._inline_code_bg
        text = re.sub(
            r"`([^`]+)`",
            rf'<code style="background-color:{code_bg};padding:2px 6px;'
            rf"border-radius:3px;font-family:Menlo,Consolas,monospace;"
            rf'font-size:14px;color:{self.c["primary"]};">\1</code>',
            text,
        )
        # 链接
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            rf'<a href="\2" style="color:{self.c["primary"]};text-decoration:none;'
            rf'border-bottom:1px solid {self.c["accent"]};">\1</a>',
            text,
        )
        return text

    # ---------- 渲染器 ----------
    def _render_heading(self, level: int, text: str) -> str:
        if level == 1:
            return (
                f'<h1 style="font-family:{self.c["font"]};'
                f"color:{self.c['primary']};font-size:24px;font-weight:bold;"
                f"margin:32px 0 16px;border-bottom:2px solid {self.c['accent']};"
                f'padding-bottom:10px;">{text}</h1>'
            )
        elif level == 2:
            return (
                f'<h2 style="color:{self.c["primary"]};font-size:20px;font-weight:bold;margin:28px 0 12px;">{text}</h2>'
            )
        elif level == 3:
            return (
                f'<h3 style="color:{self.c["primary"]};font-size:18px;font-weight:bold;margin:24px 0 10px;">{text}</h3>'
            )
        else:
            return (
                f'<h4 style="color:{self.c["accent"]};font-size:16px;font-weight:bold;margin:20px 0 8px;">{text}</h4>'
            )

    def _render_table(self, rows: list[list[str]]) -> str:
        if not rows:
            return ""
        ncols = max(len(r) for r in rows)
        width = f"{100 // ncols}%"
        border = self._table_border
        html_parts = [
            '<table style="width:100%;border-collapse:collapse;'
            'margin:20px 0;font-size:15px;border-radius:6px;overflow:hidden;">'
        ]
        for i, row in enumerate(rows):
            tag = "th" if i == 0 else "td"
            bg = self.c["primary"] if i == 0 else self._table_bg
            color = "#FFFFFF" if i == 0 else self.c["text"]
            html_parts.append("<tr>")
            for cell in row:
                html_parts.append(
                    f'<{tag} width="{width}" style="border:1px solid {border};'
                    f"padding:10px 12px;text-align:left;background-color:{bg};"
                    f"color:{color};{'font-weight:bold;' if i == 0 else ''}"
                    f'">{self._inline(cell)}</{tag}>'
                )
            html_parts.append("</tr>")
        html_parts.append("</table>")
        return "".join(html_parts)

    def _render_code(self, code: str) -> str:
        return (
            f'<pre style="background-color:{self._code_bg};color:#E0E0E0;'
            f"padding:14px 16px;border-radius:6px;overflow-x:auto;"
            f"font-family:Menlo,Consolas,monospace;font-size:13px;"
            f'line-height:1.6;margin:16px 0;"><code>'
            f"{code.replace('<', '&lt;').replace('>', '&gt;')}</code></pre>"
        )

    def _render_image(self, alt: str, src: str) -> str:
        return (
            f'<p style="text-align:center;margin:16px 0;">'
            f'<img src="{src}" alt="{alt}" '
            f'style="max-width:100%;height:auto;border-radius:6px;" /></p>'
        )

    def _extract_title(self, md: str) -> str:
        for line in md.splitlines():
            m = re.match(r"^#\s+(.*)", line)
            if m:
                return m.group(1).strip()
        return "Untitled"
