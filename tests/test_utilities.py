"""实用工具模块测试：敏感词检测 + 目录生成 + 字数统计"""

import json

from inkwell.stats import ArticleAnalyzer
from inkwell.toc import TOCGenerator
from inkwell.wordcheck import WordChecker

# ============================================================
# 敏感词检测
# ============================================================


class TestWordChecker:
    def test_clean_text_passes(self):
        checker = WordChecker()
        report = checker.check("这是一篇普通的技术文章，讲 Docker 的使用方法。")
        assert report.is_clean is True
        assert report.risk_level == "PASS"

    def test_ad_law_word_detected(self):
        checker = WordChecker()
        report = checker.check("这是市面上最好的工具。")
        assert len(report.hits) >= 1
        assert any(h.word == "最好" for h in report.hits)
        assert any(h.category == "ad-law" for h in report.hits)

    def test_multiple_ad_law_words(self):
        checker = WordChecker()
        report = checker.check("这是国家级的最先进产品，史无前例。")
        assert len(report.hits) >= 3

    def test_platform_violation_detected(self):
        checker = WordChecker()
        report = checker.check("加我微信免费领取课程。")
        assert any(h.category == "platform" for h in report.hits)

    def test_skip_categories(self):
        checker = WordChecker(check_ad_law=False)
        report = checker.check("这是最好的产品。")
        assert all(h.category != "ad-law" for h in report.hits)

    def test_report_summary_output(self):
        checker = WordChecker()
        report = checker.check("最好的工具")
        summary = report.summary()
        assert "敏感词检测报告" in summary
        assert "最好" in summary

    def test_risk_level_high(self):
        checker = WordChecker()
        text = "最好的 最大的 最高 最低 最快 最新 最优 最先进 最流行"
        report = checker.check(text)
        assert report.risk_level in ("MEDIUM", "HIGH")

    def test_code_block_ignored(self):
        checker = WordChecker()
        text = "```python\n# 最好的代码\nprint('hello')\n```"
        report = checker.check(text)
        assert report.is_clean is True

    def test_regex_pattern_detected(self):
        checker = WordChecker()
        report = checker.check("我们是全国第一的品牌。")
        assert len(report.hits) >= 1


# ============================================================
# 目录 TOC 生成
# ============================================================

SAMPLE_MD = """\
# 文章主标题

简介段落。

## 第一步：安装

内容。

### 1.1 Windows 安装

内容。

### 1.2 Mac 安装

内容。

## 第二步：配置

内容。

## 第三步：运行

内容。
"""


class TestTOCGenerator:
    def test_parse_headings(self):
        gen = TOCGenerator()
        result = gen.generate(SAMPLE_MD)
        assert result.count == 5  # 3 个 H2 + 2 个 H3

    def test_heading_levels(self):
        gen = TOCGenerator()
        result = gen.generate(SAMPLE_MD)
        levels = [h.level for h in result.headings]
        assert levels == [2, 3, 3, 2, 2]

    def test_auto_numbering(self):
        gen = TOCGenerator()
        result = gen.generate(SAMPLE_MD, show_numbers=True)
        numbers = [h.number for h in result.headings]
        assert numbers[0] == "1"  # 第一个 H2
        assert numbers[1] == "1.1"  # 第一个 H3
        assert numbers[2] == "1.2"  # 第二个 H3
        assert numbers[3] == "2"  # 第二个 H2

    def test_no_numbering(self):
        gen = TOCGenerator()
        result = gen.generate(SAMPLE_MD, show_numbers=False)
        assert all(h.number == "" for h in result.headings)

    def test_html_output_not_empty(self):
        gen = TOCGenerator()
        result = gen.generate(SAMPLE_MD)
        assert "<table" in result.html
        assert "目录" in result.html

    def test_empty_headings(self):
        gen = TOCGenerator()
        result = gen.generate("没有标题的文章。")
        assert result.is_empty is True

    def test_custom_title(self):
        gen = TOCGenerator()
        result = gen.generate(SAMPLE_MD, title="本文导航")
        assert "本文导航" in result.html

    def test_code_block_headings_ignored(self):
        gen = TOCGenerator()
        text = "## 真标题\n\n```python\n## 不是标题\n```\n"
        result = gen.generate(text)
        assert result.count == 1

    def test_theme_colors_applied(self):
        gen = TOCGenerator()
        result = gen.generate(
            SAMPLE_MD,
            theme_colors={"primary": "#FF0000", "accent": "#CCCCCC", "text": "#333333"},
        )
        assert "#FF0000" in result.html


# ============================================================
# 字数统计
# ============================================================


class TestArticleAnalyzer:
    def test_chinese_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("这是一段中文内容。")
        assert stats.chinese_chars == 8  # 这/是/一/段/中/文/内/容

    def test_english_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("This is a test sentence.")
        assert stats.english_words == 5

    def test_mixed_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("使用 Docker 构建 Python 项目。")
        assert stats.chinese_chars >= 6
        assert stats.english_words >= 2

    def test_heading_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("# 标题一\n\n## 标题二\n\n### 标题三")
        assert stats.headings == 3
        assert stats.heading_levels == [1, 2, 3]

    def test_code_block_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("```\ncode here\n```\n\n```\nmore code\n```")
        assert stats.code_blocks == 2

    def test_image_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("![图1](a.png) ![图2](b.png)")
        assert stats.images == 2

    def test_link_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("[链接1](http://a.com) 和 [链接2](http://b.com)")
        assert stats.links >= 2

    def test_reading_time(self):
        a = ArticleAnalyzer()
        long_text = "这是测试。" * 300  # 1200 个中文字
        stats = a.analyze(long_text)
        assert stats.reading_minutes >= 3.0  # 至少 3 分钟
        assert "分钟" in stats.reading_time_str

    def test_paragraph_count(self):
        a = ArticleAnalyzer()
        stats = a.analyze("段落一。\n\n段落二。\n\n段落三。")
        assert stats.paragraphs >= 3

    def test_table_count(self):
        a = ArticleAnalyzer()
        md = "| A | B |\n|---|---|\n| 1 | 2 |\n\n| C | D |\n|---|---|\n| 3 | 4 |"
        stats = a.analyze(md)
        assert stats.tables == 2

    def test_summary_output(self):
        a = ArticleAnalyzer()
        stats = a.analyze(SAMPLE_MD)
        summary = stats.summary()
        assert "文章统计" in summary
        assert "阅读时间" in summary

    def test_to_dict(self):
        a = ArticleAnalyzer()
        stats = a.analyze(SAMPLE_MD)
        d = stats.to_dict()
        assert "total_words" in d
        assert "reading_minutes" in d
        # 确保可以 JSON 序列化
        json.dumps(d, ensure_ascii=False)

    def test_code_excluded_from_word_count(self):
        a = ArticleAnalyzer()
        text_with_code = "# 标题\n\n正文内容。\n\n```python\nprint('hello world')\n```"
        stats_code = a.analyze(text_with_code)
        text_no_code = "# 标题\n\n正文内容。"
        stats_no_code = a.analyze(text_no_code)
        assert stats_code.chinese_chars == stats_no_code.chinese_chars
