"""流水线基础测试"""

import io
import re
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

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


class _LeafAudit(HTMLParser):
    """复刻 gzh-design validate_gzh_html.py 的检查逻辑

    该校验器把「中文文本节点不在 <span leaf=""> 内」判为问题，这里用同样的
    规则审计 Inkwell 的产出，避免再出现「自己过不了自己校验器」的情况。
    """

    SKIP_TAGS = {"head", "title", "style", "script"}
    CJK = re.compile(r"[\u4e00-\u9fff]")

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []
        self.leaf_depth = 0
        self.leaf_count = 0
        self.unwrapped: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        is_leaf = tag == "span" and "leaf" in dict(attrs)
        if is_leaf:
            self.leaf_count += 1
            self.leaf_depth += 1
        self.stack.append((tag, is_leaf))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, was_leaf in self.stack[i:]:
                    if was_leaf:
                        self.leaf_depth -= 1
                del self.stack[i:]
                break

    def handle_data(self, data):
        text = data.strip()
        if not text or not self.CJK.search(text):
            return
        if any(t in self.SKIP_TAGS for t, _ in self.stack):
            return
        if self.leaf_depth == 0:
            parent = self.stack[-1][0] if self.stack else "(root)"
            self.unwrapped.append((text[:24], parent))

    @classmethod
    def run(cls, html: str) -> "_LeafAudit":
        inst = cls()
        inst.feed(html)
        return inst


class TestSpanLeafWrapping:
    """文字节点必须落在 <span leaf=""> 里

    公众号编辑器只保留 leaf 内的文字样式；漏包 → 粘贴后样式大面积丢失。
    gzh-design 的 validate_gzh_html.py 直接把「全文无 span leaf」判为 ERROR，
    所以这条不是风格偏好，而是硬门槛。
    """

    def test_all_cjk_text_wrapped(self):
        html = MarkdownProcessor().convert(SAMPLE_MD)
        audit = _LeafAudit.run(html)
        assert audit.leaf_count > 0
        assert audit.unwrapped == [], f"未包裹的文本: {audit.unwrapped}"

    def test_title_not_wrapped(self):
        """<title> 里出现 <span> 是非法 HTML，不能包"""
        html = MarkdownProcessor().convert("# 测试标题\n\n正文。")
        assert "<title>测试标题</title>" in html

    def test_code_block_content_wrapped(self):
        html = MarkdownProcessor().convert("```python\n# 中文注释\nprint(1)\n```")
        audit = _LeafAudit.run(html)
        assert audit.unwrapped == []

    def test_span_leaf_not_nested_twice(self):
        """幂等：已经是 leaf 的文本不再重复包"""
        once = MarkdownProcessor._wrap_leaf('<p style="x">中文</p>')
        twice = MarkdownProcessor._wrap_leaf(once)
        assert once == twice
        assert once.count('<span leaf="">') == 1

    def test_attributes_untouched(self):
        """包裹只动文本，标签与属性必须原样保留"""
        html = MarkdownProcessor().convert("**粗体** 与 `code`")
        assert '<strong style="color:' in html
        assert '<code style="' in html
        assert "style=「" not in html

    def test_whitespace_only_not_wrapped(self):
        assert MarkdownProcessor._wrap_leaf("  \n  ") == "  \n  "

    def test_style_script_content_not_wrapped(self):
        raw = "<style>.a{color:red}</style><script>var a=1;</script><p>正文</p>"
        out = MarkdownProcessor._wrap_leaf(raw)
        assert "<style>.a{color:red}</style>" in out
        assert "<script>var a=1;</script>" in out
        assert '<span leaf="">正文</span>' in out


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

    def test_forbidden_word_in_body_text_not_flagged(self, tmp_path):
        """回归：正文讲解「linear-gradient 会被丢掉」不该被当成自己用了渐变

        扫描器早期对全文做正则，文章里只要出现这个关键词就误报。
        扫描前剥掉文本节点即可（CSS 只可能出现在标签名/属性值里）。
        """
        html_file = tmp_path / "talk.html"
        html_file.write_text(
            '<p style="color:#333;"><span leaf="">'
            "flex、grid、inline-block 和 linear-gradient 渐变在剪贴板里会被丢掉。"
            "</span></p>",
            encoding="utf-8",
        )
        v = CopyCompatValidator()
        assert v.scan(html_file) == []

    def test_real_linear_gradient_in_style_still_flagged(self, tmp_path):
        html_file = tmp_path / "grad.html"
        html_file.write_text(
            '<p style="background:linear-gradient(#fff,#000);"><span leaf="">标题</span></p>',
            encoding="utf-8",
        )
        v = CopyCompatValidator()
        warnings = v.scan(html_file)
        assert any("linear-gradient" in w for w in warnings)

    def test_missing_span_leaf_flagged(self, tmp_path):
        """中文正文一个 leaf 都没有 → 必须是警告（粘贴后样式会丢）"""
        html_file = tmp_path / "noleaf.html"
        html_file.write_text('<p style="color:#333;">中文正文</p>', encoding="utf-8")
        v = CopyCompatValidator()
        warnings = v.scan(html_file)
        assert any("span leaf" in w for w in warnings)

    def test_span_leaf_present_no_warning(self, tmp_path):
        html_file = tmp_path / "leaf.html"
        html_file.write_text('<p style="color:#333;"><span leaf="">中文正文</span></p>', encoding="utf-8")
        assert CopyCompatValidator().scan(html_file) == []

    def test_english_only_html_skips_leaf_check(self, tmp_path):
        """纯英文片段不适用 leaf 规则，不该刷警告"""
        html_file = tmp_path / "en.html"
        html_file.write_text('<p style="color:#333;">hello world</p>', encoding="utf-8")
        assert CopyCompatValidator().scan(html_file) == []


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

    def test_external_images_split_between_two_versions(self, tmp_path, monkeypatch):
        """外链图：发布版留外链，本地版内嵌 base64

        回归：两版字节完全相同（本地版失去意义，离线预览满屏裂图）。
        """
        from inkwell.processors.image_proc import ImageProcessor

        buf = io.BytesIO()
        Image.new("RGB", (1200, 800), (30, 58, 46)).save(buf, format="PNG")
        monkeypatch.setattr(ImageProcessor, "_download_bytes", lambda self, url: buf.getvalue())

        md_file = tmp_path / "ext.md"
        md_file.write_text("# 标题\n\n![图](https://cdn.example.com/a.png)\n", encoding="utf-8")
        result = Pipeline(PipelineConfig(input_md=md_file, output_dir=tmp_path / "out")).run()

        assert result.publish_html is not None and result.local_html is not None
        pub = result.publish_html.read_text(encoding="utf-8")
        local = result.local_html.read_text(encoding="utf-8")
        assert "https://cdn.example.com/a.png" in pub
        assert "https://cdn.example.com/a.png" not in local
        assert "data:image/jpeg;base64," in local
        assert result.external_embedded_images == 1
        assert pub != local
        assert result.compat_warnings == []

    def test_no_embed_external_keeps_local_version_identical(self, tmp_path, monkeypatch):
        """关掉内嵌后，本地版对外链图无能为力 —— 这正是要保留的降级开关"""
        from inkwell.processors.image_proc import ImageProcessor

        called: list[str] = []
        monkeypatch.setattr(ImageProcessor, "_download_bytes", lambda self, url: called.append(url) or b"")
        md_file = tmp_path / "ext.md"
        md_file.write_text("# 标题\n\n![图](https://cdn.example.com/a.png)\n", encoding="utf-8")
        result = Pipeline(PipelineConfig(input_md=md_file, output_dir=tmp_path / "out", embed_external=False)).run()

        assert called == []
        assert result.external_embedded_images == 0
        assert any("no-embed-external" in w for w in result.image_warnings)


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
