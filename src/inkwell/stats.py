"""字数统计与阅读时间

分析 Markdown 文章的结构化数据：
- 中文字数 / 英文词数 / 数字字符数
- 总字数（中文按字计，英文按词计）
- 段落数 / 标题数 / 代码块数 / 表格行数 / 图片数 / 链接数
- 预计阅读时长（中文 300 字/分钟，英文 200 词/分钟）
- 预计朗读时长（中文 200 字/分钟）

用法：
    analyzer = ArticleAnalyzer()
    stats = analyzer.analyze(markdown_text)
    print(stats.summary())
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ArticleStats:
    """文章统计数据"""

    # 字数统计
    chinese_chars: int = 0  # 中文字符数
    english_words: int = 0  # 英文单词数
    digits: int = 0  # 数字字符数
    punctuation: int = 0  # 标点符号数

    # 结构统计
    total_chars: int = 0  # 总字符数（含所有内容）
    paragraphs: int = 0  # 段落数（非空行）
    headings: int = 0  # 标题数
    heading_levels: list[int] = None  # 各标题层级
    code_blocks: int = 0  # 代码块数
    code_lines: int = 0  # 代码行数
    tables: int = 0  # 表格数
    table_rows: int = 0  # 表格行数
    images: int = 0  # 图片数
    links: int = 0  # 链接数
    blockquotes: int = 0  # 引用块数
    list_items: int = 0  # 列表项数
    hr_count: int = 0  # 分割线数

    # 时间估算（分钟）
    reading_minutes: float = 0.0
    speaking_minutes: float = 0.0

    def __post_init__(self) -> None:
        if self.heading_levels is None:
            self.heading_levels = []

    @property
    def total_words(self) -> int:
        """总有效字数（中文字 + 英文词）"""
        return self.chinese_chars + self.english_words

    @property
    def reading_time_str(self) -> str:
        """阅读时间（人类可读）"""
        mins = max(1, round(self.reading_minutes))
        return f"{mins} 分钟"

    @property
    def speaking_time_str(self) -> str:
        """朗读时间（人类可读）"""
        mins = max(1, round(self.speaking_minutes))
        return f"{mins} 分钟"

    def summary(self) -> str:
        """输出统计摘要"""
        lines = [
            "文章统计",
            "=" * 45,
            f"总字数（中文字 + 英文词）:  {self.total_words:,}",
            f"  中文字数:                 {self.chinese_chars:,}",
            f"  英文词数:                 {self.english_words:,}",
            f"  数字字符:                 {self.digits:,}",
            f"  标点符号:                 {self.punctuation:,}",
            f"总字符数:                   {self.total_chars:,}",
            "",
            f"段落数:                     {self.paragraphs}",
            f"标题数:                     {self.headings}",
            f"代码块:                     {self.code_blocks}（{self.code_lines} 行）",
            f"表格:                       {self.tables}（{self.table_rows} 行）",
            f"图片:                       {self.images}",
            f"链接:                       {self.links}",
            f"引用块:                     {self.blockquotes}",
            f"列表项:                     {self.list_items}",
            f"分割线:                     {self.hr_count}",
            "",
            f"预计阅读时间:               {self.reading_time_str}",
            f"预计朗读时间:               {self.speaking_time_str}",
        ]

        if self.heading_levels:
            level_dist: dict[int, int] = {}
            for lv in self.heading_levels:
                level_dist[lv] = level_dist.get(lv, 0) + 1
            dist_str = ", ".join(f"H{k}: {v}" for k, v in sorted(level_dist.items()))
            lines.append(f"标题层级分布:               {dist_str}")

        lines.append("=" * 45)
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """转为 dict（方便 JSON 序列化）"""
        return {
            "total_words": self.total_words,
            "chinese_chars": self.chinese_chars,
            "english_words": self.english_words,
            "digits": self.digits,
            "paragraphs": self.paragraphs,
            "headings": self.headings,
            "code_blocks": self.code_blocks,
            "images": self.images,
            "links": self.links,
            "reading_minutes": round(self.reading_minutes, 1),
            "speaking_minutes": round(self.speaking_minutes, 1),
        }


class ArticleAnalyzer:
    """文章结构分析器

    用法：
        analyzer = ArticleAnalyzer()
        stats = analyzer.analyze(markdown_text)
        print(stats.summary())
    """

    # 阅读速度（字/分钟）
    READING_SPEED_CN = 300  # 中文阅读 300 字/分钟
    READING_SPEED_EN = 200  # 英文阅读 200 词/分钟
    SPEAKING_SPEED_CN = 200  # 中文朗读 200 字/分钟

    # 正则
    RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)")
    RE_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    RE_LINK = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
    RE_LIST = re.compile(r"^\s*[-*+]\s+|^\s*\d+\.\s+")
    RE_HR = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
    RE_TABLE = re.compile(r"^\|.*\|$")
    RE_CHINESE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
    RE_ENGLISH = re.compile(r"[a-zA-Z]+")
    RE_DIGIT = re.compile(r"[0-9]")
    RE_PUNCT = re.compile(r"[，。！？、；：" "''「」【】（）《》…—,.!?:;\"'(){}-]")

    def analyze(self, md_text: str) -> ArticleStats:
        """分析 Markdown 文本，返回统计数据"""
        stats = ArticleStats()
        lines = md_text.splitlines()
        in_code = False

        # 先提取纯文本内容（排除代码块）做字数统计
        prose_lines: list[str] = []
        code_content_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                if in_code:
                    in_code = False
                else:
                    in_code = True
                    stats.code_blocks += 1
                continue

            if in_code:
                code_content_lines.append(line)
                continue

            prose_lines.append(line)

        stats.code_lines = len(code_content_lines)

        # 逐行分析结构
        for line in prose_lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                continue

            # 标题
            m = self.RE_HEADING.match(stripped)
            if m:
                stats.headings += 1
                level = len(m.group(1))
                stats.heading_levels.append(level)
                # 标题也算段落
                stats.paragraphs += 1
                continue

            # 分割线
            if self.RE_HR.match(stripped):
                stats.hr_count += 1
                continue

            # 引用
            if stripped.startswith(">"):
                stats.blockquotes += 1
                continue

            # 列表项
            if self.RE_LIST.match(stripped):
                stats.list_items += 1
                continue

            # 表格行
            if self.RE_TABLE.match(stripped):
                stats.table_rows += 1
                # 表格分隔行不计
                if not re.match(r"^\|[\s:|-]+\|$", stripped):
                    stats.table_rows += 0  # 已经加了
                continue

            # 段落
            stats.paragraphs += 1

        # 统计表格数（连续的表格行算一个表格）
        stats.tables = self._count_tables(prose_lines)

        # 图片和链接（全文扫描）
        stats.images = len(self.RE_IMAGE.findall(md_text))
        # 链接 = 所有 [...]()  匹配 - 图片数
        all_links = len(self.RE_LINK.findall(md_text))
        stats.links = max(0, all_links)

        # 字数统计（排除代码块和 Markdown 标记）
        prose_text = "\n".join(prose_lines)
        # 去掉 Markdown 语法标记符号
        clean = prose_text
        clean = re.sub(r"```[^`]*```", "", clean)  # 代码块
        clean = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", clean)  # 图片
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)  # 链接保留文字
        clean = re.sub(r"^#{1,6}\s+", "", clean, flags=re.MULTILINE)  # 标题标记
        clean = re.sub(r"^>\s*", "", clean, flags=re.MULTILINE)  # 引用标记
        clean = re.sub(r"^\s*[-*+]\s+", "", clean, flags=re.MULTILINE)  # 列表标记
        clean = re.sub(r"^\s*\d+\.\s+", "", clean, flags=re.MULTILINE)  # 有序列表
        clean = re.sub(r"^---+$", "", clean, flags=re.MULTILINE)  # 分割线
        clean = re.sub(r"\|", "", clean)  # 表格竖线
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)  # 粗体
        clean = re.sub(r"\*([^*]+)\*", r"\1", clean)  # 斜体
        clean = re.sub(r"==([^=]+)==", r"\1", clean)  # 高亮
        clean = re.sub(r"`([^`]+)`", r"\1", clean)  # 行内代码

        stats.chinese_chars = len(self.RE_CHINESE.findall(clean))
        stats.english_words = len(self.RE_ENGLISH.findall(clean))
        stats.digits = len(self.RE_DIGIT.findall(clean))
        stats.punctuation = len(self.RE_PUNCT.findall(clean))
        stats.total_chars = len(md_text)

        # 时间估算
        cn_minutes = stats.chinese_chars / self.READING_SPEED_CN
        en_minutes = stats.english_words / self.READING_SPEED_EN
        stats.reading_minutes = cn_minutes + en_minutes

        stats.speaking_minutes = stats.chinese_chars / self.SPEAKING_SPEED_CN

        return stats

    def _count_tables(self, lines: list[str]) -> int:
        """统计表格数（连续的表格行算一个）"""
        count = 0
        prev_was_table = False

        for line in lines:
            is_table = bool(self.RE_TABLE.match(line.strip()))
            if is_table and not prev_was_table:
                count += 1
            prev_was_table = is_table

        return count
