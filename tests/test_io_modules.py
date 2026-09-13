"""图片处理与发布模块测试

覆盖此前零测试的两个模块：
- processors/image_proc.py：压缩、CDN 上传、失败降级、本地预览双轨替换
- publisher.py：正文深度提取、纯文本化、剪贴板富文本写入、微信草稿参数校验

这两个模块处在「复制到公众号」这条主链路上，任何回归都会直接毁掉发布体验，
所以关键路径全部用回归测试锁死。
"""

from __future__ import annotations

import io
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


def _png_bytes(size: tuple[int, int] = (1200, 800)) -> bytes:
    """内存里的 PNG，用来假装从外链下载回来的图片"""
    buf = io.BytesIO()
    Image.new("RGB", size, (30, 58, 46)).save(buf, format="PNG")
    return buf.getvalue()


@contextmanager
def _serve_image(payload: bytes):
    """起一个本地 HTTP 服务器托管图片，返回可访问的 URL

    真跑 urllib 那条下载路径（而不是 monkeypatch 掉），能顺带验证
    UA 头、超时与 read 上限；不依赖外网，跑测试时也快。
    """

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):  # 静音
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/a.png"
    finally:
        server.shutdown()
        server.server_close()


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
    def test_data_uri_untouched_with_warning(self, tmp_path):
        """base64 内嵌图原样保留，但要告警（公众号会过滤 data:image）"""
        html = '<img src="data:image/png;base64,AAAA">'
        proc = ImageProcessor()
        new, _ = proc.process_html(html, tmp_path)
        assert new == html
        assert any("data:image" in w for w in proc.warnings)

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

    def test_corrupt_local_image_skipped_with_warning(self, tmp_path):
        """文件存在但不是图片（下载中断/存成 HTML 错误页）→ 告警跳过，不崩"""
        (tmp_path / "bad.png").write_text("not an image", encoding="utf-8")
        proc = ImageProcessor()
        new, uploads = proc.process_html('<img src="bad.png">', tmp_path)
        assert new == '<img src="bad.png">'
        assert uploads == []
        assert any("压缩失败" in w for w in proc.warnings)


class TestExternalImageEmbedding:
    """回归：正文图本来就是外链时，本地预览版必须仍能内嵌

    背景：process_html() 早期对 http(s) 一律原样返回且不记 _local_map，
    to_local_preview() 就替换不到任何东西 —— 两个版本字节完全相同，
    IDE 预览面板加载不了外网时满屏裂图，本地版等于没有。
    """

    def test_publish_keeps_url_local_embeds_base64(self, tmp_path, monkeypatch):
        src = "https://cdn.example.com/a.png"
        monkeypatch.setattr(ImageProcessor, "_download_bytes", lambda self, url: _png_bytes())
        proc = ImageProcessor()
        pub, uploads = proc.process_html(f'<img src="{src}">', tmp_path)

        assert pub == f'<img src="{src}">'  # 发布版保留原外链
        assert uploads == [src]  # 但计数里要看得见
        assert proc.embedded_external == [src]

        local = proc.to_local_preview(pub)
        assert "data:image/jpeg;base64," in local
        assert src not in local  # 整段替换，不留 URL 前缀

    def test_download_failure_warns_with_reason(self, tmp_path, monkeypatch):
        def boom(self, url):
            raise OSError("HTTP Error 404: Not Found")

        monkeypatch.setattr(ImageProcessor, "_download_bytes", boom)
        proc = ImageProcessor()
        src = "https://cdn.example.com/missing.png"
        pub, _ = proc.process_html(f'<img src="{src}">', tmp_path)

        assert pub == f'<img src="{src}">'  # 失败不阻断，发布版不受影响
        assert len(proc.warnings) == 1
        assert "404" in proc.warnings[0]  # 告警必须带具体原因
        assert proc.to_local_preview(pub) == pub  # 没进 map，无从替换
        assert proc.embedded_external == []

    def test_embed_external_disabled_skips_download(self, tmp_path, monkeypatch):
        called: list[str] = []
        monkeypatch.setattr(ImageProcessor, "_download_bytes", lambda self, url: called.append(url) or b"")
        proc = ImageProcessor(embed_external=False)
        pub, _ = proc.process_html('<img src="https://cdn.example.com/a.png">', tmp_path)

        assert called == []
        assert any("no-embed-external" in w for w in proc.warnings)

    def test_oversize_external_skipped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(ImageProcessor, "_download_bytes", lambda self, url: b"x" * 2048)
        proc = ImageProcessor(max_download_bytes=1024)
        proc.process_html('<img src="https://cdn.example.com/big.png">', tmp_path)

        assert proc.embedded_external == []
        assert any("上限" in w for w in proc.warnings)

    def test_non_image_external_skipped_with_reason(self, tmp_path, monkeypatch):
        """外链下回来是 HTML 错误页时，要报「解码失败」而不是崩掉"""
        monkeypatch.setattr(ImageProcessor, "_download_bytes", lambda self, url: b"<html>404</html>")
        proc = ImageProcessor()
        proc.process_html('<img src="https://cdn.example.com/fake.png">', tmp_path)

        assert proc.embedded_external == []
        assert any("解码失败" in w for w in proc.warnings)

    def test_same_url_embedded_once(self, tmp_path, monkeypatch):
        """同一张外链图出现多次，map 里只留一条，替换时一次覆盖全部"""
        src = "https://cdn.example.com/a.png"
        monkeypatch.setattr(ImageProcessor, "_download_bytes", lambda self, url: _png_bytes())
        proc = ImageProcessor()
        pub, uploads = proc.process_html(f'<img src="{src}"><img src="{src}">', tmp_path)

        assert uploads == [src, src]
        assert list(proc._local_map) == [src]
        local = proc.to_local_preview(pub)
        assert src not in local
        assert local.count("data:image/jpeg;base64,") == 2


class TestExternalDownloadOverHttp:
    """真跑一次 urllib 下载（本地 HTTP 服务器），不 mock 网络层"""

    def test_download_bytes_returns_payload(self):
        payload = _png_bytes((40, 30))
        with _serve_image(payload) as url:
            assert ImageProcessor()._download_bytes(url) == payload

    def test_read_is_capped_at_limit_plus_one(self):
        """超限图只读上限 +1 字节就够判超限，不该把整个大文件拉下来"""
        payload = b"x" * 5000
        with _serve_image(payload) as url:
            raw = ImageProcessor(max_download_bytes=1024)._download_bytes(url)
        assert len(raw) == 1025

    def test_end_to_end_external_image_embeds(self, tmp_path):
        payload = _png_bytes((1200, 800))
        with _serve_image(payload) as url:
            proc = ImageProcessor()
            pub, uploads = proc.process_html(f'<img src="{url}">', tmp_path)
            local = proc.to_local_preview(pub)

        assert uploads == [url]
        assert url in pub
        assert "data:image/jpeg;base64," in local
        assert proc.warnings == []


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


class TestCdnConfigGuard:
    """CDN 配置不全时必须降级，绝不能产出畸形外链

    回归背景：_upload 用 f"{cdn_base}/{path}" 拼返回地址，若 cdn_base 为空就会
    得到 "/pic.jpg" 这种畸形相对地址，粘进公众号后图片全裂。所以「token+repo 齐备
    但缺 cdn_base」应判定为不可用，而不是可用但地址是坏的。
    """

    def test_missing_cdn_base_does_not_upload(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        _make_image(tmp_path / "pic.png")
        calls: list[str] = []

        def spy(self, data, filename):
            calls.append(filename)
            return f"/{filename}"  # 真被调用就会产出畸形地址

        monkeypatch.setattr(ImageProcessor, "_upload", spy)
        proc = ImageProcessor(github_token="fake-token", github_repo="me/repo", cdn_base="")
        new, _ = proc.process_html('<img src="pic.png">', tmp_path)

        assert calls == [], "缺 cdn_base 时不应尝试上传"
        assert "data:image/jpeg;base64," in new
        assert 'src="/pic.png"' not in new
        assert any("cdn_base" in w for w in proc.warnings)

    def test_missing_repo_does_not_upload(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        _make_image(tmp_path / "pic.png")
        calls: list[str] = []

        def spy(self, data, filename):
            calls.append(filename)
            return "https://cdn.example.com/img/x.png"

        monkeypatch.setattr(ImageProcessor, "_upload", spy)
        proc = ImageProcessor(
            github_token="fake-token",
            github_repo="",
            cdn_base="https://cdn.example.com/img",
        )
        new, _ = proc.process_html('<img src="pic.png">', tmp_path)

        assert calls == []
        assert "data:image/jpeg;base64," in new


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
        # 这个用例验证的是 AppleScript 命令的构造方式，与运行平台无关，
        # 所以必须把 shutil.which 一并 mock 掉；否则在 Linux / Windows 上
        # _copy_html_macos 会因为找不到 osascript 直接抛 RuntimeError。
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/osascript")
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
