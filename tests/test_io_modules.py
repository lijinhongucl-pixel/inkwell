"""图片处理与发布模块测试

覆盖此前零测试的两个模块：
- processors/image_proc.py：压缩、CDN 上传、失败降级、本地预览双轨替换
- publisher.py：正文深度提取、纯文本化、剪贴板富文本写入、微信草稿参数校验

这两个模块处在「复制到公众号」这条主链路上，任何回归都会直接毁掉发布体验，
所以关键路径全部用回归测试锁死。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from inkwell.processors.image_proc import ImageProcessor
from inkwell.publisher import Publisher

# ============================================================
# 测试素材
# ============================================================


def _make_image(path: Path, size: tuple[int, int] = (1200, 800)) -> Path:
    Image.new("RGB", size, (30, 58, 46)).save(path)
    return path


# ============================================================
# ImageProcessor
# ============================================================


class TestImageProcessorCompress:
    def test_resize_to_max_width(self, tmp_path):
        src = _make_image(tmp_path / "wide.png", (1200, 800))
        raw = ImageProcessor(max_width=600)._compress(src)
        import io

        img = Image.open(io.BytesIO(raw))
        assert img.width == 600
        assert img.height == 400  # 等比缩放

    def test_not_upscale_small_image(self, tmp_path):
        src = _make_image(tmp_path / "small.png", (200, 100))
        raw = ImageProcessor(max_width=600)._compress(src)
        import io

        assert Image.open(io.BytesIO(raw)).width == 200

    def test_rgba_converted_to_rgb(self, tmp_path):
        """带 alpha 的图必须转 RGB，否则 JPEG 存不下会报错"""
        src = tmp_path / "alpha.png"
        Image.new("RGBA", (100, 100), (30, 58, 46, 128)).save(src)
        raw = ImageProcessor()._compress(src)
        import io

        assert Image.open(io.BytesIO(raw)).mode == "RGB"

    def test_quality_respected(self, tmp_path):
        """质量参数越低，产物越小"""
        src = _make_image(tmp_path / "q.png")
        high = len(ImageProcessor(quality=95)._compress(src))
        low = len(ImageProcessor(quality=20)._compress(src))
        assert low < high


class TestProcessHtml:
    def test_remote_url_untouched(self, tmp_path):
        html = '<p><img src="https://cdn.example.com/a.png"></p>'
        new, uploads = ImageProcessor().process_html(html, tmp_path)
        assert new == html
        assert uploads == []

    def test_data_uri_untouched(self, tmp_path):
        html = '<img src="data:image/png;base64,AAAA">'
        new, _ = ImageProcessor().process_html(html, tmp_path)
        assert new == html

    def test_plain_text_src_not_matched(self, tmp_path):
        """回归：早期用 src="..." 通配，会把 <script src> 之类也卷进来"""
        html = '<script src="app.js"></script>'
        new, _ = ImageProcessor().process_html(html, tmp_path)
        assert new == html

    def test_no_token_degrades_to_data_uri(self, tmp_path):
        _make_image(tmp_path / "pic.png")
        new, uploads = ImageProcessor(github_token="", github_repo="").process_html('<img src="pic.png">', tmp_path)
        assert "data:image/jpeg;base64," in new
        assert len(uploads) == 1
        assert uploads[0].startswith("data:image")

    def test_token_uploads_to_cdn(self, tmp_path, monkeypatch):
        _make_image(tmp_path / "pic.png")
        proc = ImageProcessor(
            cdn_base="https://cdn.example.com/img",
            github_token="t",
            github_repo="me/repo",
        )
        monkeypatch.setattr(
            ImageProcessor,
            "_upload",
            lambda self, data, fn: f"https://cdn.example.com/img/{fn}",
        )
        new, uploads = proc.process_html('<img src="pic.png">', tmp_path)
        assert "cdn.example.com/img/pic.png" in new
        assert "data:image" not in new
        assert uploads == ["https://cdn.example.com/img/pic.png"]

    def test_upload_failure_falls_back(self, tmp_path, monkeypatch):
        """回归：上传失败以前会抛异常中断整条流水线"""
        _make_image(tmp_path / "pic.png")
        proc = ImageProcessor(
            cdn_base="https://cdn.example.com/img",
            github_token="t",
            github_repo="me/repo",
        )

        def boom(self, data, fn):
            raise RuntimeError("502 Bad Gateway")

        monkeypatch.setattr(ImageProcessor, "_upload", boom)
        new, uploads = proc.process_html('<img src="pic.png">', tmp_path)
        assert "data:image/jpeg;base64," in new
        assert len(proc.warnings) == 1
        assert "502" in proc.warnings[0]

    def test_missing_image_skipped_with_warning(self, tmp_path):
        proc = ImageProcessor()
        new, uploads = proc.process_html('<img src="nope.png">', tmp_path)
        assert new == '<img src="nope.png">'
        assert uploads == []
        assert len(proc.warnings) == 1


class TestLocalPreviewDualTrack:
    def test_cdn_replaced_by_base64(self, tmp_path, monkeypatch):
        _make_image(tmp_path / "pic.png")
        proc = ImageProcessor(
            cdn_base="https://cdn.example.com/img",
            github_token="t",
            github_repo="me/repo",
        )
        cdn = "https://cdn.example.com/img/pic.png"
        monkeypatch.setattr(ImageProcessor, "_upload", lambda self, d, fn: cdn)
        pub, _ = proc.process_html('<img src="pic.png">', tmp_path)
        local = proc.to_local_preview(pub)

        assert cdn in pub
        assert cdn not in local
        assert "data:image/jpeg;base64," in local

    def test_no_prefix_contamination(self, tmp_path, monkeypatch):
        """回归：整段替换不能残留 URL 前缀

        早期用正则保留前缀再拼 base64，会产出
        `...@main/dir/data:image/png;base64,...` 导致图片全裂。
        """
        _make_image(tmp_path / "pic.png")
        proc = ImageProcessor(
            cdn_base="https://cdn.example.com/img",
            github_token="t",
            github_repo="me/repo",
        )
        monkeypatch.setattr(
            ImageProcessor,
            "_upload",
            lambda self, d, fn: "https://cdn.example.com/img/pic.png",
        )
        pub, _ = proc.process_html('<img src="pic.png">', tmp_path)
        local = proc.to_local_preview(pub)
        assert "cdn.example.com/img/data:image" not in local
        assert "cdn.example.com" not in local

    def test_no_upload_map_is_noop(self):
        proc = ImageProcessor()
        html = '<img src="https://cdn.example.com/a.png">'
        assert proc.to_local_preview(html) == html


# ============================================================
# Publisher
# ============================================================

NESTED_HTML = (
    "<!DOCTYPE html><html><head></head><body>"
    '<section id="outer">'
    "<p>开头</p>"
    '<section id="toc"><p>目录卡片</p></section>'
    "<p>中间</p>"
    '<section id="img"><p>图片卡片</p></section>'
    "<p>结尾</p>"
    "</section>"
    "</body></html>"
)


class TestExtractSection:
    def test_keeps_nested_sections(self):
        """回归：非贪婪正则会停在第一个 </section>，把正文截断"""
        body = Publisher._extract_section(NESTED_HTML)
        assert "开头" in body
        assert "目录卡片" in body
        assert "图片卡片" in body
        assert "结尾" in body
        assert body.count("</section>") == 3

    def test_returns_empty_without_section(self):
        assert Publisher._extract_section("<p>纯段落</p>") == ""

    def test_handles_unclosed_section(self):
        body = Publisher._extract_section("<section><p>没闭合</p>")
        assert "没闭合" in body

    def test_ignores_head_and_body_wrapper(self):
        body = Publisher._extract_section(NESTED_HTML)
        assert "<body>" not in body
        assert body.startswith("<section")


class TestStripTags:
    def test_tags_removed_and_entities_decoded(self):
        text = Publisher._strip_tags('<p style="margin:0;">A&amp;B</p><p>C</p>')
        assert text == "A&B\nC"

    def test_block_tags_become_newlines(self):
        text = Publisher._strip_tags("<h1>标题</h1><p>正文</p>")
        assert text.splitlines() == ["标题", "正文"]

    def test_br_becomes_newline(self):
        assert Publisher._strip_tags("上<br/>下").splitlines() == ["上", "下"]

    def test_empty_paragraphs_dropped(self):
        assert Publisher._strip_tags("<p></p><p>正文</p>") == "正文"


class TestClipboardHtml:
    def test_macos_writer_sets_html_flavor(self, monkeypatch, tmp_path):
        """回归：剪贴板必须带 HTML flavor，只写纯文本会让公众号粘到源码"""
        captured = {}

        class FakeProc:
            returncode = 0
            stderr = b""

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return FakeProc()

        monkeypatch.setattr("subprocess.run", fake_run)
        Publisher._copy_html_macos("<p>正文</p>", "正文")
        script = captured["cmd"][2]
        assert "«class HTML»" in script
        assert "string:t" in script
        # 两个临时文件路径作为 argv 传入，避免源码里的引号转义问题
        assert len(captured["cmd"]) == 5

    def test_macos_writer_raises_on_failure(self, monkeypatch):
        class FakeProc:
            returncode = 1
            stderr = b"osascript boom"

        monkeypatch.setattr("subprocess.run", lambda *a, **k: FakeProc())
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/osascript")
        with pytest.raises(RuntimeError, match="osascript boom"):
            Publisher._copy_html_macos("<p>x</p>", "x")

    def test_plain_copy_reports_missing_command(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        ok, msg = Publisher._copy_plain("x")
        assert ok is False
        assert "剪贴板命令" in msg


class TestWechatDraft:
    def test_missing_credentials(self, monkeypatch):
        monkeypatch.delenv("WECHAT_APP_ID", raising=False)
        monkeypatch.delenv("WECHAT_APP_SECRET", raising=False)
        r = Publisher().publish_to_wechat(Path("x.html"), title="t")
        assert r.success is False
        assert "WECHAT_APP_ID" in r.message

    def test_missing_thumb_media_id(self, monkeypatch, tmp_path):
        """回归：以前兜底成 'default_thumb'，必被微信以 40007 拒绝"""
        monkeypatch.setenv("WECHAT_APP_ID", "id")
        monkeypatch.setenv("WECHAT_APP_SECRET", "secret")
        monkeypatch.setattr(Publisher, "_get_access_token", lambda self, a, s: "tok")
        f = tmp_path / "a.html"
        f.write_text("<section><p>x</p></section>", encoding="utf-8")
        r = Publisher().publish_to_wechat(f, title="t")
        assert r.success is False
        assert "thumb" in r.message.lower() or "封面" in r.message
