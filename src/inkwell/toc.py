"""文章目录 TOC 自动生成

从 Markdown 标题解析出层级结构，生成公众号剪贴板兼容的目录卡片 HTML。
卡片采用内联样式 + table 布局，可插在文章开头。

用法：
    generator = TOCGenerator()
    toc_html = generator.generate(markdown_text, theme_colors={
        "primary": "#059669", "accent": "#A7F3D0", "text": "#1F2937",
    })
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Heading:
    """单个标题条目"""

    level: int  # 1-4
    text: str  # 标题文字（已去 Markdown 标记）
    number: str = ""  # 编号（如 "1" / "1.2" / "1.2.3"）


@dataclass
class TOCResult:
    """TOC 生成结果"""

    headings: list[Heading] = field(default_factory=list)
    html: str = ""

    @property
    def is_empty(self) -> bool:
        return len(self.headings) == 0

    @property
    def count(self) -> int:
        return len(self.headings)


class TOCGenerator:
    """文章目录生成器

    用法：
        gen = TOCGenerator()
        result = gen.generate(md_text, theme_colors={"primary": "#059669"})
        print(result.html)  # 插在文章开头
    """

    # 仅提取 h2 和 h3（h1 是文章标题，h4 太细）
    MIN_LEVEL = 2
    MAX_LEVEL = 3

    def generate(
        self,
        md_text: str,
        *,
        theme_colors: dict[str, str] | None = None,
        show_numbers: bool = True,
        title: str = "目录",
    ) -> TOCResult:
        """解析 Markdown 生成目录卡片 HTML

        Args:
            md_text:      Markdown 原文
            theme_colors: 主题色板（需要 primary, accent, text 三个 key）
            show_numbers: 是否显示自动编号
            title:        目录卡片标题
        """
        colors = theme_colors or {}
        primary = colors.get("primary", "#059669")
        accent = colors.get("accent", "#A7F3D0")
        text_color = colors.get("text", "#1F2937")

        headings = self._parse_headings(md_text)

        if show_numbers:
            headings = self._assign_numbers(headings)

        html = self._render_toc_card(
            headings,
            primary,
            accent,
            text_color,
            title,
        )

        return TOCResult(headings=headings, html=html)

    def _parse_headings(self, md: str) -> list[Heading]:
        """从 Markdown 文本提取标题"""
        headings: list[Heading] = []
        in_code = False

        for line in md.splitlines():
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue

            m = re.match(r"^(#{2,3})\s+(.*)", line)
            if m:
                level = len(m.group(1))
                raw_text = m.group(2).strip()
                # 去掉 Markdown 内联标记
                clean_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", raw_text)
                clean_text = re.sub(r"\*([^*]+)\*", r"\1", clean_text)
                clean_text = re.sub(r"`([^`]+)`", r"\1", clean_text)
                clean_text = re.sub(r"==([^=]+)==", r"\1", clean_text)
                headings.append(Heading(level=level, text=clean_text))

        return headings

    def _assign_numbers(self, headings: list[Heading]) -> list[Heading]:
        """自动编号：h2 → 1, 2, 3...；h3 → 1.1, 1.2, 2.1..."""
        counters = [0, 0, 0, 0]  # h1-h4
        result: list[Heading] = []

        for h in headings:
            counters[h.level - 1] += 1
            # 下级编号重置
            for i in range(h.level, 4):
                counters[i] = 0

            parts = [str(counters[i]) for i in range(h.level) if counters[i] > 0]
            h.number = ".".join(parts)
            result.append(h)

        return result

    def _render_toc_card(
        self,
        headings: list[Heading],
        primary: str,
        accent: str,
        text_color: str,
        title: str,
    ) -> str:
        """渲染公众号兼容的目录卡片"""
        if not headings:
            return ""

        rows: list[str] = []

        # 卡片头部
        rows.append(
            f'<table style="width:100%;border-collapse:collapse;'
            f"margin:16px 0;border-radius:8px;overflow:hidden;"
            f'border-left:3px solid {primary};">'
        )

        # 标题行
        rows.append(
            f'<tr><td style="background-color:{primary};'
            f"padding:10px 16px;color:#FFFFFF;font-size:15px;"
            f'font-weight:bold;">{title}</td></tr>'
        )

        # 内容行
        items_html: list[str] = []
        for h in headings:
            indent = "" if h.level == 2 else "&nbsp;&nbsp;&nbsp;&nbsp;"
            dot = f'<span style="color:{accent};font-weight:bold;">{h.number}</span>' if h.number else ""
            items_html.append(
                f'{dot}<span style="margin-left:6px;color:{text_color};'
                f"font-size:{'15px' if h.level == 2 else '14px'};"
                f"{'font-weight:600;' if h.level == 2 else ''}"
                f'line-height:2;">{indent}{h.text}</span>'
            )

        items_str = "<br/>".join(items_html)

        rows.append(f'<tr><td style="background-color:#FAFAFA;padding:12px 16px;">{items_str}</td></tr>')

        rows.append("</table>")

        return "".join(rows)
