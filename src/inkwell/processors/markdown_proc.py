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

# ============================================================
# 主题色板
# ============================================================
THEMES: dict[str, dict[str, str]] = {
    # --- 摸鱼绿 ---
    "moyu-green": {
        "bg": "#FFFFFF",
        "text": "#1F2937",
        "primary": "#059669",
        "accent": "#A7F3D0",
        "highlight": "#065F46",
        "underline": "#A7F3D0",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 红白色系 ---
    "red-white": {
        "bg": "#FFFFFF",
        "text": "#1F2937",
        "primary": "#DC2626",
        "accent": "#FECACA",
        "highlight": "#991B1B",
        "underline": "#FECACA",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 石墨极简风 ---
    "graphite-minimal": {
        "bg": "#FAFAFA",
        "text": "#3F3F46",
        "primary": "#52525B",
        "accent": "#A1A1AA",
        "highlight": "#27272A",
        "underline": "#52525B",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 留白禅意风 ---
    "zen-whitespace": {
        "bg": "#FDFCFB",
        "text": "#3D4F44",
        "primary": "#4A5D52",
        "accent": "#B5C8BC",
        "highlight": "#2D3B33",
        "underline": "#B5C8BC",
        "font": "'Songti SC', 'Noto Serif SC', serif",
    },
    # --- 摸鱼票据风 ---
    "moyu-ticket": {
        "bg": "#FFFBEB",
        "text": "#1F2937",
        "primary": "#059669",
        "accent": "#FCD34D",
        "highlight": "#92400E",
        "underline": "#A7F3D0",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 橄榄手记 ---
    "olive-journal": {
        "bg": "#F5F5F0",
        "text": "#2C2C2A",
        "primary": "#1E1F23",
        "accent": "#ED7B2F",
        "highlight": "#1E1F23",
        "underline": "#ED7B2F",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 经典衬线（原 editorial-oldmoney） ---
    "classic-serif": {
        "bg": "#FAF8F5",
        "text": "#2C2C2A",
        "primary": "#1B3A2E",
        "accent": "#C8A35E",
        "highlight": "#5C1A1B",
        "underline": "#C8A35E",
        "font": "Georgia, 'Songti SC', 'Noto Serif SC', serif",
    },
    # --- 赛博朋克霓虹（暗色科技风） ---
    "cyber-neon": {
        "bg": "#0D0D1A",
        "text": "#C8C8E0",
        "primary": "#00F0FF",
        "accent": "#FF00AA",
        "highlight": "#FFD700",
        "underline": "#00F0FF",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 咖啡摩卡（暖调生活风） ---
    "coffee-mocha": {
        "bg": "#F5EDE0",
        "text": "#3E2C1C",
        "primary": "#6F4E37",
        "accent": "#C9A87C",
        "highlight": "#8B5A2B",
        "underline": "#C9A87C",
        "font": "Georgia, 'Songti SC', serif",
    },
    # --- 海洋蓝（商务财经风） ---
    "ocean-blue": {
        "bg": "#FFFFFF",
        "text": "#1A2B3C",
        "primary": "#0066CC",
        "accent": "#4FC3F7",
        "highlight": "#0D47A1",
        "underline": "#4FC3F7",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 日落暖橙（生活方式风） ---
    "sunset-warm": {
        "bg": "#FFF8F0",
        "text": "#4A2C20",
        "primary": "#E76F51",
        "accent": "#F4A261",
        "highlight": "#A8472A",
        "underline": "#F4A261",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 水墨山水（传统文化风） ---
    "ink-wash": {
        "bg": "#F8F6F1",
        "text": "#2B2B2B",
        "primary": "#1A1A1A",
        "accent": "#888888",
        "highlight": "#555555",
        "underline": "#AAAAAA",
        "font": "'Songti SC', 'Noto Serif SC', serif",
    },
    # --- 森林深绿（自然环保风） ---
    "forest-deep": {
        "bg": "#F4F7F5",
        "text": "#1C3329",
        "primary": "#2D6A4F",
        "accent": "#95D5B2",
        "highlight": "#1B4332",
        "underline": "#95D5B2",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 皇家紫（创意设计风） ---
    "royal-purple": {
        "bg": "#FAF7FF",
        "text": "#2D1B4E",
        "primary": "#6A1B9A",
        "accent": "#CE93D8",
        "highlight": "#4A148C",
        "underline": "#CE93D8",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 樱花粉（时尚美妆风） ---
    "sakura-pink": {
        "bg": "#FFF5F7",
        "text": "#3D2020",
        "primary": "#E91E63",
        "accent": "#F8BBD0",
        "highlight": "#AD1457",
        "underline": "#F8BBD0",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
}

# 向后兼容别名
THEMES["editorial-oldmoney"] = THEMES["classic-serif"]

# 主题元信息（用于 CLI 列表展示）
THEME_META: list[dict[str, str]] = [
    {"id": "moyu-green", "name": "摸鱼绿", "desc": "教程、测评、清单、工具盘点"},
    {"id": "red-white", "name": "红白色系", "desc": "深度分析、观点、力量感话题"},
    {"id": "graphite-minimal", "name": "石墨极简", "desc": "设计、科技评论、专业观点"},
    {"id": "zen-whitespace", "name": "留白禅意", "desc": "禅意、极简生活、深度随笔"},
    {"id": "moyu-ticket", "name": "摸鱼票据", "desc": "测评、工具对比（票据视觉）"},
    {"id": "olive-journal", "name": "橄榄手记", "desc": "内刊手记、深度评测、案例复盘"},
    {"id": "classic-serif", "name": "经典衬线", "desc": "深度长文、编辑部风格"},
    {"id": "cyber-neon", "name": "赛博霓虹", "desc": "科技、AI、编程、暗色酷炫"},
    {"id": "coffee-mocha", "name": "咖啡摩卡", "desc": "生活、美食、旅行、暖调随笔"},
    {"id": "ocean-blue", "name": "海洋蓝", "desc": "商务、财经、行业分析、职场"},
    {"id": "sunset-warm", "name": "日落暖橙", "desc": "生活方式、品牌故事、情感"},
    {"id": "ink-wash", "name": "水墨山水", "desc": "传统文化、诗词、人文历史"},
    {"id": "forest-deep", "name": "森林深绿", "desc": "环保、自然、可持续发展、健康"},
    {"id": "royal-purple", "name": "皇家紫", "desc": "创意、设计、艺术、灵感"},
    {"id": "sakura-pink", "name": "樱花粉", "desc": "时尚、美妆、穿搭、少女心"},
]

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
