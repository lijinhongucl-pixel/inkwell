"""流水线基础测试"""

from pathlib import Path

from inkwell.core import Pipeline, PipelineConfig
from inkwell.processors.markdown_proc import MarkdownProcessor
from inkwell.processors.validator import CopyCompatValidator

SAMPLE_MD = """\
# 测试标题

这是第一段正文，讲一个**重点**和一个「中文引号」。

## 二级标题

- 列表项一
- 列表项二

| 列A | 列B |
|-----|-----|
| 数据1 | 数据2 |

> 引用块内容

```python
print("hello")
```

---

结尾段落。
"""


class TestMarkdownProcessor:
    def test_convert_returns_complete_html(self):
        proc = MarkdownProcessor()
        html = proc.convert(SAMPLE_MD)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_no_flex_grid_inline_block(self):
        """铁律：正文不能出现 flex / grid / inline-block"""
        proc = MarkdownProcessor()
        html = proc.convert(SAMPLE_MD)
        forbidden = ["display:flex", "display:grid", "display:inline-block", "display: flex"]
        for f in forbidden:
            assert f not in html, f"发现禁止样式: {f}"

    def test_no_linear_gradient(self):
        proc = MarkdownProcessor()
        html = proc.convert(SAMPLE_MD)
        assert "linear-gradient" not in html

    def test_no_svg(self):
        proc = MarkdownProcessor()
        html = proc.convert(SAMPLE_MD)
        assert "<svg" not in html

    def test_table_uses_td_width(self):
        proc = MarkdownProcessor()
        html = proc.convert(SAMPLE_MD)
        assert "<table" in html
        assert 'width="50%"' in html  # 两列均分

    def test_bullet_uses_character(self):
        proc = MarkdownProcessor()
        html = proc.convert("- 项目一")
        assert "●" in html  # 用户记忆：用字符不用CSS圆点

    def test_separator_uses_dash_chars(self):
        proc = MarkdownProcessor()
        html = proc.convert("---")
        assert "———" in html

    def test_heading_has_bottom_border(self):
        proc = MarkdownProcessor()
        html = proc.convert("# 大标题")
        assert "border-bottom" in html

    def test_quote_replacement_preserves_html_attributes(self):
        """回归测试：引号替换不得破坏 HTML 属性（v0.7.1 致命 bug）"""
        proc = MarkdownProcessor()
        # 包含英文双引号的段落
        html = proc.convert('This is "quoted text" here.')
        # HTML 属性的双引号完好
        assert 'style="' in html
        # 不应出现 style=「 这种崩溃写法
        assert "style=「" not in html
        # 用户文本中的引号应被替换成中文「」
        assert '"' not in html.split("<body")[1].split(">This is ")[1].split(" here.")[0]

    def test_inline_code_preserves_quotes_in_style(self):
        """行内代码生成的 HTML style 属性引号不被替换"""
        proc = MarkdownProcessor()
        html = proc.convert("Use `print()` function.")
        assert '<code style="' in html
        assert "style=「" not in html

    def test_bold_preserves_quotes_in_style(self):
        """粗体生成的 HTML style 属性引号不被替换"""
        proc = MarkdownProcessor()
        html = proc.convert("**bold text**")
        assert '<strong style="' in html
        assert "style=「" not in html

    def test_chinese_quotes_in_user_text(self):
        """用户文本中的英文双引号转为成对中文引号「」"""
        proc = MarkdownProcessor()
        html = proc.convert('He said "hello" to her.')
        # 应该出现中文引号
        assert "「" in html
        assert "」" in html
        # HTML 属性仍然完好
        assert 'style="' in html


class TestCopyCompatValidator:
    def test_clean_html_passes(self, tmp_path):
        html_file = tmp_path / "test.html"
        html_file.write_text('<p style="color:#333;">clean</p>', encoding="utf-8")
        v = CopyCompatValidator()
        assert v.scan(html_file) == []

    def test_flex_detected(self, tmp_path):
        html_file = tmp_path / "bad.html"
        html_file.write_text('<div style="display:flex;">bad</div>', encoding="utf-8")
        v = CopyCompatValidator()
        warnings = v.scan(html_file)
        assert len(warnings) > 0
        assert any("flex" in w for w in warnings)

    def test_base64_image_detected(self, tmp_path):
        html_file = tmp_path / "b64.html"
        html_file.write_text('<img src="data:image/png;base64,iVBOR..." />', encoding="utf-8")
        v = CopyCompatValidator()
        warnings = v.scan(html_file)
        assert any("base64" in w for w in warnings)


class TestPipelineIntegration:
    def test_full_pipeline_produces_html(self, tmp_path):
        md_file = tmp_path / "article.md"
        md_file.write_text(SAMPLE_MD, encoding="utf-8")
        out_dir = tmp_path / "output"

        cfg = PipelineConfig(
            input_md=md_file,
            output_dir=out_dir,
            emit_local_preview=False,
            strict_copy_compat=True,
        )
        result = Pipeline(cfg).run()
        assert result.publish_html is not None
        assert result.publish_html.exists()
        # 兼容性校验应通过（无图片、无 flex）
        assert result.compat_warnings == []


class TestNewThemes:
    """测试 v0.5 新增的 8 套主题"""

    NEW_THEME_IDS = [
        "cyber-neon",
        "coffee-mocha",
        "ocean-blue",
        "sunset-warm",
        "ink-wash",
        "forest-deep",
        "royal-purple",
        "sakura-pink",
    ]

    def test_all_new_themes_exist(self):
        for tid in self.NEW_THEME_IDS:
            proc = MarkdownProcessor(theme=tid)
            assert proc.theme_name == tid

    def test_all_new_themes_produce_valid_html(self):
        for tid in self.NEW_THEME_IDS:
            proc = MarkdownProcessor(theme=tid)
            html = proc.convert(SAMPLE_MD)
            assert "<!DOCTYPE html>" in html
            assert "</html>" in html
            assert "border-bottom" in html  # h1 有底部边框

    def test_all_new_themes_no_flex(self):
        """所有新主题都必须通过公众号兼容性铁律"""
        for tid in self.NEW_THEME_IDS:
            proc = MarkdownProcessor(theme=tid)
            html = proc.convert(SAMPLE_MD)
            for forbidden in ["display:flex", "display:grid", "display:inline-block"]:
                assert forbidden not in html, f"主题 {tid} 含禁止样式 {forbidden}"

    def test_total_theme_count_is_15(self):
        """从 THEME_META 确认主题总数"""
        themes = MarkdownProcessor.list_themes()
        assert len(themes) == 15

    def test_dark_theme_adapts_quote_bg(self):
        """cyber-neon 是暗色主题，引用块底色应为暗色"""
        proc = MarkdownProcessor(theme="cyber-neon")
        assert proc._is_dark is True
        html = proc.convert("> 引用内容")
        # 暗色引用不应使用 #F0F0F0
        assert "#F0F0F0" not in html

    def test_light_theme_uses_light_quote_bg(self):
        """ocean-blue 是浅色主题，引用块底色应为浅色（主题色混合，非固定灰色）"""
        proc = MarkdownProcessor(theme="ocean-blue")
        assert proc._is_dark is False
        html = proc.convert("> 引用内容")
        # 暗色引用不应使用 #2A2A3A
        assert "#2A2A3A" not in html


class TestHtmlCommentStripping:
    """回归：草稿占位符用 HTML 注释写成，排版时必须整段剥离

    否则 `generate` 产出的占位提示会漏进正文，用户看到的是
    「TODO: 结论先行」这种没写完的痕迹。
    """

    def test_single_line_comment_removed(self):
        proc = MarkdownProcessor()
        html = proc.convert("<!-- TODO: 填写内容 -->\n\n正文段落。")
        assert "TODO" not in html
        assert "<!--" not in html
        assert "正文段落" in html

    def test_inline_comment_stripped_keeps_text(self):
        """同一行里既有注释又有正文时，只去掉注释"""
        proc = MarkdownProcessor()
        html = proc.convert("前<!-- 注释 -->后")
        assert "注释" not in html
        assert "前后" in html

    def test_multiline_comment_removed(self):
        proc = MarkdownProcessor()
        html = proc.convert("<!-- 第一行\n第二行\n第三行 -->\n正文。")
        assert "第一行" not in html
        assert "第三行" not in html
        assert "正文" in html

    def test_comment_inside_code_block_preserved(self):
        """代码块里的注释是内容，不能剥"""
        proc = MarkdownProcessor()
        html = proc.convert("```html\n<!-- 这是代码 -->\n```")
        assert "这是代码" in html

    def test_empty_paragraph_not_emitted(self):
        """纯注释行不应产生空段落"""
        proc = MarkdownProcessor()
        html = proc.convert("<!-- 只有注释 -->")
        assert "<p" not in html


class TestDraftGeneratorPlaceholders:
    """回归：草稿占位符必须是注释形式，不能是裸文本"""

    def test_placeholder_is_html_comment(self):
        from inkwell.generator import DraftGenerator

        md = DraftGenerator().generate("测试主题", style="review")
        # 占位符存在（供写作者参考）
        assert "<!-- TODO:" in md
        # 不能有裸 TODO 行（会被渲染成可见正文）
        for line in md.splitlines():
            assert not line.strip().startswith("TODO:")

    def test_draft_renders_without_placeholder_junk(self):
        """草稿直接过一遍排版，不应残留占位文字"""
        from inkwell.generator import DraftGenerator

        md = DraftGenerator().generate("测试主题", style="tutorial")
        html = MarkdownProcessor().convert(md)
        assert "TODO" not in html
        assert "在此填写" not in html


class TestThemeRegistry:
    """主题注册表一致性

    `THEMES`（可用色板）与 `THEME_META`（对外展示列表）是两份数据，
    历史上出现过「色板存在但没登记」导致 `inkwell themes` 列不出来的情况。
    """

    def test_all_meta_ids_resolvable(self):
        """THEME_META 里登记的 id 必须都能真实实例化"""
        for meta in MarkdownProcessor.list_themes():
            proc = MarkdownProcessor(theme=meta["id"])
            assert proc.c["bg"].startswith("#")

    def test_legacy_alias_still_works(self):
        """editorial-oldmoney 是 classic-serif 的向后兼容别名，不能悄悄失效"""
        from inkwell.processors.markdown_proc import THEMES

        assert "editorial-oldmoney" in THEMES
        assert THEMES["editorial-oldmoney"] == THEMES["classic-serif"]
        # 别名能直接用于渲染
        assert "body" in MarkdownProcessor(theme="editorial-oldmoney").convert("# 标题")

    def test_meta_has_no_duplicate_ids(self):
        ids = [m["id"] for m in MarkdownProcessor.list_themes()]
        assert len(ids) == len(set(ids))

    def test_every_theme_renders(self):
        """16 个可用色板逐一渲染，保证没有半成品主题"""
        from inkwell.processors.markdown_proc import THEMES

        for tid in THEMES:
            html = MarkdownProcessor(theme=tid).convert("# 标题\n\n正文 **粗体**。")
            assert "<h1" in html
            assert "**" not in html  # 粗体必须被转换掉

    def test_packaged_assets_exist(self):
        """pyproject 的 package-data 声明的资源必须真实存在"""
        pkg = Path(__file__).resolve().parent.parent / "src" / "inkwell"
        assert (pkg / "screenshot.js").is_file()
        assert (pkg / "py.typed").is_file()
