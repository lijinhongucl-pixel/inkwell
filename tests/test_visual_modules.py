"""封面、社交卡片、设计审计、封面顾问测试"""

import pytest

from inkwell.cover_advisor import CoverAdvisor
from inkwell.cover_gen import CoverGenerator, CoverSpec
from inkwell.design_audit import DesignAuditor, GateStatus
from inkwell.social_card import CardPage, CardSpec, SocialCardGenerator


class TestCoverGenerator:
    def test_generate_wide_and_square(self, tmp_path):
        gen = CoverGenerator()
        spec = CoverSpec(
            title_prefix="最懂",
            title_em="生活",
            title_suffix="的 AI",
            kicker="开源模型 · 反向出海",
            subtitle_en="When the library meets the street.",
            lede="一句话导读叙事。",
            slogan="创前沿智能 · 解生活之问",
            issue_no="08",
            issue_date="2026.08",
            data_bar=[
                ("75.1", "", "T-Bench"),
                ("280", "B", "总参"),
                ("16", "B", "激活"),
                ("512", "K", "上下文"),
            ],
        )
        wide, square = gen.generate(spec, output_dir=tmp_path)
        assert wide.exists()
        assert square.exists()
        assert "21x9" in wide.name
        assert "1x1" in square.name

    def test_cover_has_vds_schema(self, tmp_path):
        gen = CoverGenerator()
        spec = CoverSpec(title_prefix="测试", title_em="封面")
        wide, _ = gen.generate(spec, output_dir=tmp_path)
        html = wide.read_text(encoding="utf-8")
        assert 'data-vds-schema="v3.1"' in html

    def test_cover_has_watermark(self, tmp_path):
        gen = CoverGenerator()
        spec = CoverSpec(title_prefix="测", issue_no="09")
        wide, _ = gen.generate(spec, output_dir=tmp_path)
        assert "material" in wide.read_text(encoding="utf-8")

    def test_data_bar_rendered(self, tmp_path):
        gen = CoverGenerator()
        spec = CoverSpec(
            title_prefix="x",
            data_bar=[("100", "ms", "延迟"), ("200", "MB", "体积")],
        )
        wide, _ = gen.generate(spec, output_dir=tmp_path)
        html = wide.read_text(encoding="utf-8")
        assert "100" in html
        assert "延迟" in html


class TestSocialCardGenerator:
    def test_generate_xhs_cards(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="xhs",
            style="swiss",
            pages=[
                CardPage(title="封面标题", subtitle="副标题", body="正文要点"),
                CardPage(title="第二页", body="内容"),
                CardPage(title="第三页", body="更多内容"),
            ],
            brand="测试品牌",
            tag="#测试标签",
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        assert len(paths) == 3
        for p in paths:
            assert p.exists()
        assert "cover" in paths[0].name
        assert "p2" in paths[1].name

    def test_invalid_platform_raises(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(platform="nonexistent")
        with pytest.raises(ValueError):
            gen.generate(spec, output_dir=tmp_path)

    def test_invalid_style_raises(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(platform="xhs", style="nonexistent", pages=[CardPage(title="x")])
        with pytest.raises(ValueError):
            gen.generate(spec, output_dir=tmp_path)

    def test_card_has_format(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(platform="xhs", style="editorial", pages=[CardPage(title="test")])
        paths = gen.generate(spec, output_dir=tmp_path)
        html = paths[0].read_text(encoding="utf-8")
        assert 'data-vds-format="3x4"' in html

    def test_list_platforms(self):
        platforms = SocialCardGenerator.list_platforms()
        ids = [p["id"] for p in platforms]
        assert "xhs" in ids
        assert "wechat-cover" in ids

    def test_list_styles(self):
        styles = SocialCardGenerator.list_styles()
        ids = [s["id"] for s in styles]
        assert "swiss" in ids
        assert "editorial" in ids

    def test_global_platforms_available(self):
        """海外平台全部在 PLATFORM_SPECS 中"""
        platforms = SocialCardGenerator.list_platforms()
        ids = [p["id"] for p in platforms]
        for pid in ("instagram-feed", "instagram-story", "x-twitter", "linkedin", "pinterest", "youtube-thumb"):
            assert pid in ids, f"平台 {pid} 不存在"

    def test_instagram_feed_1x1(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="instagram-feed",
            style="swiss",
            pages=[
                CardPage(title="Cover", subtitle="Swipe to learn"),
                CardPage(title="Point 1", body="Key takeaway"),
                CardPage(title="Point 2", body="Another insight"),
            ],
            brand="@yourbrand",
            tag="#TechTips",
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        assert len(paths) == 3
        html = paths[0].read_text(encoding="utf-8")
        assert "data-vds-format" in html
        assert 'lang="en"' in html  # 海外平台用英文

    def test_instagram_story_9x16(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="instagram-story",
            style="editorial",
            pages=[CardPage(title="Story Card")],
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        html = paths[0].read_text(encoding="utf-8")
        assert "aspect-ratio:9/16" in html

    def test_x_twitter_16x9(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="x-twitter",
            style="dark-bold",
            pages=[CardPage(title="Hot Take")],
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        html = paths[0].read_text(encoding="utf-8")
        assert "aspect-ratio:16/9" in html

    def test_pinterest_2x3(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="pinterest",
            style="clean-light",
            pages=[CardPage(title="DIY Guide")],
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        html = paths[0].read_text(encoding="utf-8")
        assert "aspect-ratio:2/3" in html

    def test_linkedin_generates(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="linkedin",
            style="swiss",
            pages=[CardPage(title="Professional Post")],
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        assert len(paths) == 1
        assert paths[0].exists()

    def test_youtube_thumb_16x9(self, tmp_path):
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="youtube-thumb",
            style="dark-bold",
            pages=[CardPage(title="Must Watch")],
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        html = paths[0].read_text(encoding="utf-8")
        assert "aspect-ratio:16/9" in html

    def test_total_platform_count(self):
        """11 个平台（5 中文 + 5 海外 + 1 通用）"""
        platforms = SocialCardGenerator.list_platforms()
        assert len(platforms) == 11


class TestLayoutFillsCanvas:
    """回归：内容必须垂直撑满画布，不能全堆在顶部留大片空白"""

    def test_card_uses_three_row_table(self, tmp_path):
        """卡片用三段式 table（顶部/中部/底部）+ height:100% 撑满"""
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="xhs",
            style="editorial",
            pages=[CardPage(title="封面", subtitle="副标题", body="正文")],
            brand="Brand",
            tag="#tag",
        )
        html = gen.generate(spec, output_dir=tmp_path)[0].read_text(encoding="utf-8")
        assert "height:100%" in html
        assert "vertical-align:middle" in html
        assert "vertical-align:top" in html
        assert "vertical-align:bottom" in html

    def test_card_has_watermark(self, tmp_path):
        """卡片背景带期号水印，填充留白"""
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="xhs",
            style="editorial",
            pages=[
                CardPage(title="封面", subtitle="s", body="b"),
                CardPage(title="第二页", subtitle="s", body="b"),
            ],
            brand="Brand",
            tag="#tag",
        )
        paths = gen.generate(spec, output_dir=tmp_path)
        assert "01" in paths[0].read_text(encoding="utf-8")
        assert "02" in paths[1].read_text(encoding="utf-8")

    def test_no_bottom_absolute_footer(self, tmp_path):
        """页脚改用 table 行定位，不再依赖 absolute（避免布局割裂）"""
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="xhs",
            style="editorial",
            pages=[CardPage(title="封面", subtitle="s", body="b")],
            brand="Brand",
            tag="#tag",
        )
        html = gen.generate(spec, output_dir=tmp_path)[0].read_text(encoding="utf-8")
        assert "position:absolute;bottom:" not in html

    def test_cover_uses_table_layout(self, tmp_path):
        """封面同样用三段式 table，标题垂直居中"""
        gen = CoverGenerator()
        spec = CoverSpec(
            title_prefix="测",
            title_em="试",
            title_suffix="",
            kicker="栏目",
            subtitle_en="Subtitle",
            lede="导读",
            slogan="口号",
            issue_no="01",
            issue_date="2026.09",
            data_bar=[("30", "秒", "耗时")],
        )
        wide, square = gen.generate(spec, output_dir=tmp_path)
        for p in (wide, square):
            html = p.read_text(encoding="utf-8")
            assert "height:100%" in html
            assert "vertical-align:middle" in html

    def test_data_bar_colors_follow_spec(self, tmp_path):
        """数据条配色跟随封面 accent/ink，不硬编码金色"""
        gen = CoverGenerator()
        spec = CoverSpec(
            title_prefix="T",
            title_em="",
            title_suffix="",
            kicker="K",
            subtitle_en="S",
            lede="L",
            slogan="SL",
            issue_no="01",
            issue_date="2026.09",
            data_bar=[("1", "", "a")],
            accent_color="#ff0000",
            ink_color="#00ff00",
        )
        wide, _ = gen.generate(spec, output_dir=tmp_path)
        html = wide.read_text(encoding="utf-8")
        assert "#ff0000" in html
        assert "#00ff00" in html
        assert "#d4a04a" not in html  # 旧的硬编码金色已消失

    def test_data_bar_container_has_no_blanket_opacity(self, tmp_path):
        """数据条容器不能整体加 opacity（会把数字和标签一起压暗）"""
        gen = CoverGenerator()
        spec = CoverSpec(
            title_prefix="T",
            title_em="",
            title_suffix="",
            kicker="K",
            subtitle_en="S",
            lede="L",
            slogan="SL",
            issue_no="01",
            issue_date="2026.09",
            data_bar=[("1", "", "a")],
        )
        wide, square = gen.generate(spec, output_dir=tmp_path)
        for p in (wide, square):
            html = p.read_text(encoding="utf-8")
            for line in html.splitlines():
                if "display:table;width:100%" in line:
                    assert "opacity" not in line


class TestScreenshotDegradation:
    """回归：缺 Playwright 时必须优雅降级，不能抛 Node 堆栈"""

    def test_screenshot_error_class_exists(self):
        from inkwell.screenshot import ScreenshotError

        assert issubclass(ScreenshotError, RuntimeError)

    def test_is_available_returns_bool(self):
        from inkwell.screenshot import Screenshotter

        assert isinstance(Screenshotter.is_available(), bool)

    def test_check_ready_raises_with_install_hint(self, monkeypatch):
        from inkwell.screenshot import ScreenshotError, Screenshotter

        shooter = Screenshotter()
        monkeypatch.setattr(shooter, "_node_path", None)
        with pytest.raises(ScreenshotError) as exc:
            shooter.check_ready()
        assert "playwright-core" in str(exc.value)

    def test_card_png_degrades_gracefully(self, tmp_path, capsys):
        """PNG 不可用时仍返回 HTML 路径，不抛异常"""
        import inkwell.social_card as sc
        from inkwell.screenshot import Screenshotter

        gen = sc.SocialCardGenerator()
        spec = CardSpec(
            platform="xhs",
            style="editorial",
            pages=[CardPage(title="封面", subtitle="s", body="b")],
            brand="Brand",
            tag="#tag",
        )
        if Screenshotter.is_available():
            pytest.skip("本机 Playwright 可用，跳过降级路径")
        paths = gen.generate(spec, output_dir=tmp_path, png=True)
        assert paths[0].suffix == ".html"


class TestDesignAuditor:
    def test_audit_good_cover_passes(self, tmp_path):
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head><body>
<section data-vds-schema="v3.1">
  <h1 style="font-size:96px;letter-spacing:-2px;color:#ECE2CF;">Big Title</h1>
  <h2 style="font-size:32px;">Subtitle</h2>
  <span style="font-size:16px;color:#D4A04A;">accent</span>
  <p style="border-left:3px solid #D4A04A;padding-left:12px;">quote</p>
  <p style="border-left:3px solid #888;padding-left:12px;">quote2</p>
  <img src="https://cdn.example.com/img.png" />
</section></body></html>"""
        f = tmp_path / "cover.html"
        f.write_text(html, encoding="utf-8")
        auditor = DesignAuditor()
        report = auditor.audit_html_cover(f)
        assert report.all_passed

    def test_audit_missing_title_fails_gate1(self, tmp_path):
        html = '<html><head><meta charset="UTF-8"></head><body><p>no title</p></body></html>'
        f = tmp_path / "bad.html"
        f.write_text(html, encoding="utf-8")
        auditor = DesignAuditor()
        report = auditor.audit_html_cover(f)
        gate1 = report.gates[0]
        assert gate1.status == GateStatus.FAIL

    def test_audit_base64_image_fails_gate3(self, tmp_path):
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head><body>
<h1 style="font-size:48px;">Title</h1>
<h2 style="font-size:24px;">Sub</h2>
<img src="data:image/png;base64,iVBOR..." />
</body></html>"""
        f = tmp_path / "b64.html"
        f.write_text(html, encoding="utf-8")
        auditor = DesignAuditor()
        report = auditor.audit_html_cover(f)
        gate3 = report.gates[2]
        assert gate3.status == GateStatus.FAIL

    def test_audit_low_visual_density_warns_gate2(self, tmp_path):
        html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head><body>
<h1 style="font-size:24px;">Small Title</h1>
<p style="color:#333;">text</p>
</body></html>"""
        f = tmp_path / "thin.html"
        f.write_text(html, encoding="utf-8")
        auditor = DesignAuditor()
        report = auditor.audit_html_cover(f)
        gate2 = report.gates[1]
        assert gate2.status == GateStatus.WARN

    def test_audit_report_summary(self, tmp_path):
        html = '<html><head><meta charset="UTF-8"></head><body><h1 style="font-size:48px;">x</h1><h2 style="font-size:24px;">y</h2></body></html>'
        f = tmp_path / "simple.html"
        f.write_text(html, encoding="utf-8")
        auditor = DesignAuditor()
        report = auditor.audit_html_article(f)
        summary = report.summary()
        assert "Design Audit" in summary
        assert "Gate 1" in summary


class TestCoverAdvisor:
    def test_advise_tutorial_recommends_big_title_or_screenshot(self):
        advisor = CoverAdvisor()
        r = advisor.advise(topic="Docker 教程", article_type="tutorial")
        assert r.pattern_id in ("big-title", "screenshot-evidence", "before-after")

    def test_advise_comparison_topic(self):
        advisor = CoverAdvisor()
        r = advisor.advise(topic="Docker vs Podman 对比评测", article_type="comparison")
        assert r.pattern_id in ("data-comparison", "before-after")

    def test_advise_list_topic(self):
        advisor = CoverAdvisor()
        r = advisor.advise(topic="10 个好用工具推荐", article_type="list")
        assert r.pattern_id in ("list-countdown", "big-title")

    def test_advise_keyword_signal_optimization(self):
        advisor = CoverAdvisor()
        r = advisor.advise(topic="镜像优化提速技巧", article_type="tutorial")
        # "优化" 和 "提速" 是 before-after 的信号词
        assert r.pattern_id in ("big-title", "screenshot-evidence", "before-after")

    def test_advise_multi_returns_multiple(self):
        advisor = CoverAdvisor()
        results = advisor.advise_multi(topic="测试", article_type="general", top_n=3)
        assert len(results) == 3
        ids = [r.pattern_id for r in results]
        assert len(set(ids)) == 3  # 不重复

    def test_advise_has_actionable_tips(self):
        advisor = CoverAdvisor()
        r = advisor.advise(topic="x", article_type="general")
        assert len(r.title_tips) >= 2
        assert len(r.avoid) >= 1
        assert r.color_suggestion
        assert r.layout_hint

    def test_list_patterns(self):
        patterns = CoverAdvisor.list_patterns()
        assert len(patterns) == 6
        ids = [p["id"] for p in patterns]
        assert "big-title" in ids
        assert "data-comparison" in ids
