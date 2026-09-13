"""搜索和草稿生成器测试"""

import pytest

from inkwell.generator import DraftGenerator
from inkwell.searcher import ContentSearcher, SearchResult


class TestContentSearcher:
    def test_search_result_to_markdown_row(self):
        r = SearchResult(
            title="foo/bar",
            url="https://github.com/foo/bar",
            source="github",
            description="A cool project",
            stars=1234,
            language="Python",
        )
        row = r.to_markdown_row()
        assert "[foo/bar]" in row
        assert "1234" in row

    def test_to_markdown_empty(self):
        md = ContentSearcher.to_markdown([], title="测试")
        assert "无结果" in md

    def test_to_markdown_with_stars(self):
        results = [
            SearchResult(title="proj", url="http://x", source="github", description="d", stars=100),
        ]
        md = ContentSearcher.to_markdown(results, title="热门")
        assert "Stars" in md
        assert "proj" in md

    def test_to_markdown_without_stars(self):
        results = [
            SearchResult(title="web-page", url="http://x", source="web", description="d"),
        ]
        md = ContentSearcher.to_markdown(results)
        assert "来源" in md
        assert "web" in md

    def test_invalid_source_raises(self):
        s = ContentSearcher()
        with pytest.raises(ValueError):
            s.search("test", source="nonexistent")


class TestDraftGenerator:
    def test_generate_general_has_title(self):
        gen = DraftGenerator()
        md = gen.generate("测试主题", style="general")
        assert "# 测试主题" in md

    def test_generate_tutorial_has_sections(self):
        gen = DraftGenerator()
        md = gen.generate("Docker", style="tutorial")
        assert "## 环境准备" in md
        assert "## 常见问题" in md

    def test_generate_review_has_conclusion_first(self):
        gen = DraftGenerator()
        md = gen.generate("工具X", style="review")
        assert "## 结论先行" in md
        assert "## 信源与免责声明" in md

    def test_generate_outline_only(self):
        gen = DraftGenerator()
        md = gen.generate("主题", style="tutorial", outline_only=True)
        assert "## 大纲" in md
        assert "TODO" not in md

    def test_generate_invalid_style_raises(self):
        gen = DraftGenerator()
        with pytest.raises(ValueError):
            gen.generate("x", style="nonexistent")

    def test_list_styles(self):
        styles = DraftGenerator.list_styles()
        ids = [s["id"] for s in styles]
        assert "tutorial" in ids
        assert "review" in ids
        assert len(styles) == 5

    def test_intro_contains_topic(self):
        gen = DraftGenerator()
        md = gen.generate("我的话题", style="opinion")
        assert "我的话题" in md
