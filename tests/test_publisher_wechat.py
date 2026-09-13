"""微信草稿链路测试

用假 urlopen 替身接管所有出网请求，断言**发了哪些请求、请求体长什么样**，
不依赖真实凭证，也不碰真实微信接口。

覆盖四道闸门：
1. 本地长度校验（不通过时一次请求都不该发）
2. access_token 请求参数
3. 正文图转存 media/uploadimg + 封面 material/add_material
4. draft/add 载荷字段
"""

from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import pytest

from inkwell.publisher import Publisher

SECTION_HTML = (
    '<!DOCTYPE html><html><body><section id="outer"><p>开头</p>'
    '<section id="toc"><p>目录</p></section><p>结尾</p></section></body></html>'
)


def png_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (6, 4), (12, 34, 56)).save(buf, format="PNG")
    return buf.getvalue()


def gif_bytes() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (6, 4), (12, 34, 56)).save(buf, format="GIF")
    return buf.getvalue()


def b64_data_url(raw: bytes) -> str:
    import base64

    return "data:image/png;base64," + base64.b64encode(raw).decode()


class FakeResp:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class WechatStub:
    """假微信服务器：按 URL 路由，记录每一次调用"""

    def __init__(self, *, token_ok: bool = True, uploadimg: dict | None = None, material: dict | None = None):
        self.token_ok = token_ok
        self.uploadimg = uploadimg
        self.material = material
        self.calls: list[dict] = []
        self._img_seq = 0

    def __call__(self, req, timeout=None):
        url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        body = getattr(req, "data", None)
        self.calls.append({"url": url, "body": body})

        if "/cgi-bin/token" in url:
            if self.token_ok:
                return FakeResp(json.dumps({"access_token": "TOK", "expires_in": 7200}).encode())
            return FakeResp(json.dumps({"errcode": 40164, "errmsg": "invalid ip 1.2.3.4, not in whitelist"}).encode())
        if "/media/uploadimg" in url:
            if self.uploadimg is not None:
                return FakeResp(json.dumps(self.uploadimg).encode())
            self._img_seq += 1
            return FakeResp(json.dumps({"url": f"https://mmbiz.qpic.cn/mock{self._img_seq}.jpg"}).encode())
        if "/material/add_material" in url:
            if self.material is not None:
                return FakeResp(json.dumps(self.material).encode())
            return FakeResp(
                json.dumps({"media_id": "THUMB_MEDIA_ID", "url": "https://mmbiz.qpic.cn/thumb.jpg"}).encode()
            )
        if "/draft/add" in url:
            return FakeResp(json.dumps({"media_id": "DRAFT_MEDIA_ID"}).encode())
        # 剩下的当作图片下载
        return FakeResp(png_bytes())

    def urls(self) -> list[str]:
        return [c["url"] for c in self.calls]

    def only(self, needle: str) -> list[dict]:
        return [c for c in self.calls if needle in c["url"]]


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("WECHAT_APP_ID", "wxTESTAPPID")
    monkeypatch.setenv("WECHAT_APP_SECRET", "test_secret")


@pytest.fixture
def stub(monkeypatch):
    s = WechatStub()
    monkeypatch.setattr("urllib.request.urlopen", s)
    return s


def write(section: str, path: Path) -> Path:
    path.write_text(f"<!DOCTYPE html><html><body>{section}</body></html>", encoding="utf-8")
    return path


class TestLengthValidation:
    """微信对 title/author/digest 有硬性字数上限，本地必须先拦"""

    @pytest.mark.parametrize(
        ("field", "value", "hint"),
        [
            ("title", "标" * 33, "32"),
            ("author", "名" * 17, "16"),
            ("digest", "摘" * 129, "128"),
        ],
    )
    def test_rejects_overlong_field(self, env, stub, tmp_path, field, value, hint):
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        kwargs = {"title": "正常标题", "thumb_media_id": "T"}
        kwargs[field] = value
        r = Publisher().publish_to_wechat(f, **kwargs)
        assert r.success is False
        assert hint in r.message
        assert stub.calls == [], "本地校验失败时不该发出任何请求"

    def test_rejects_empty_title(self, env, stub, tmp_path):
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="", thumb_media_id="T")
        assert r.success is False
        assert stub.calls == []

    def test_missing_thumb_and_image_reports_both_options(self, env, stub, tmp_path):
        """回归：缺封面要在取 token 之前拦掉，别白花一次调用"""
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t")
        assert r.success is False
        assert "--thumb-image" in r.message and "--thumb" in r.message
        assert stub.calls == []


class TestDraftPayload:
    def test_token_params_and_payload_shape(self, env, stub, tmp_path):
        f = write(
            '<section><p>正文</p><section id="toc"><p>目录</p></section></section>',
            tmp_path / "a.html",
        )
        r = Publisher().publish_to_wechat(f, title="标题", author="名流", thumb_media_id="PERM_ID")
        assert r.success is True
        assert r.media_id == "DRAFT_MEDIA_ID"

        token_url = stub.only("/cgi-bin/token")[0]["url"]
        assert "grant_type=client_credential" in token_url
        assert "appid=wxTESTAPPID" in token_url
        assert "secret=test_secret" in token_url

        draft = stub.only("/draft/add")
        assert len(draft) == 1
        assert "access_token=TOK" in draft[0]["url"]
        payload = json.loads(draft[0]["body"])
        art = payload["articles"][0]
        assert art["title"] == "标题"
        assert art["author"] == "名流"
        assert art["thumb_media_id"] == "PERM_ID"
        assert art["need_open_comment"] == 0
        assert art["only_fans_can_comment"] == 0
        assert art["content"].startswith("<section")
        assert "目录" in art["content"], "嵌套 section 不能被截断"
        assert "<!DOCTYPE" not in art["content"]

    def test_digest_omitted_when_empty_so_wechat_autofills(self, env, stub, tmp_path):
        f = write("<section><p>正文</p></section>", tmp_path / "a.html")
        Publisher().publish_to_wechat(f, title="标题", thumb_media_id="T")
        art = json.loads(stub.only("/draft/add")[0]["body"])["articles"][0]
        assert "digest" not in art

    def test_digest_passed_through_when_given(self, env, stub, tmp_path):
        f = write("<section><p>正文</p></section>", tmp_path / "a.html")
        Publisher().publish_to_wechat(f, title="标题", thumb_media_id="T", digest="一句话摘要")
        art = json.loads(stub.only("/draft/add")[0]["body"])["articles"][0]
        assert art["digest"] == "一句话摘要"


class TestImageTransfer:
    """回归：微信 draft/add 会过滤外链图，正文图必须先换成 mmbiz 地址"""

    def test_data_url_image_is_uploaded_and_replaced(self, env, stub, tmp_path):
        f = write(f'<section><p>x</p><img src="{b64_data_url(png_bytes())}"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert r.success is True
        assert (r.images_total, r.images_transferred) == (1, 1)
        assert r.warnings == []

        up = stub.only("/media/uploadimg")
        assert len(up) == 1
        assert b'name="media"' in up[0]["body"]
        assert b"image/png" in up[0]["body"]

        content = json.loads(stub.only("/draft/add")[0]["body"])["articles"][0]["content"]
        assert "data:image" not in content, "base64 内嵌图必须被换掉"
        assert "https://mmbiz.qpic.cn/mock1.jpg" in content

    def test_http_image_is_downloaded_then_uploaded(self, env, stub, tmp_path):
        f = write('<section><img src="https://cdn.example.com/a.png"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert (r.images_total, r.images_transferred) == (1, 1)
        assert stub.only("cdn.example.com"), "应当先把外链图下载回来"
        content = json.loads(stub.only("/draft/add")[0]["body"])["articles"][0]["content"]
        assert "cdn.example.com" not in content
        assert "mmbiz.qpic.cn" in content

    def test_relative_local_image_is_read_from_html_dir(self, env, stub, tmp_path):
        (tmp_path / "pic.png").write_bytes(png_bytes())
        f = write('<section><img src="./pic.png"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert (r.images_total, r.images_transferred) == (1, 1)

    def test_already_wechat_hosted_image_is_skipped(self, env, stub, tmp_path):
        f = write('<section><img src="https://mmbiz.qpic.cn/old.jpg"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert (r.images_total, r.images_transferred) == (0, 0)
        assert stub.only("/media/uploadimg") == []

    def test_non_web_image_is_converted_to_jpeg(self, env, stub, tmp_path):
        """微信 uploadimg 只吃 jpg/png，GIF 之类要先用 Pillow 转掉"""
        f = write(f'<section><img src="{b64_data_url(gif_bytes())}"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert r.images_transferred == 1
        assert b"image/jpeg" in stub.only("/media/uploadimg")[0]["body"]

    def test_single_image_failure_warns_but_still_pushes_draft(self, monkeypatch, env, tmp_path):
        """一张图转存失败不该阻断推送，但必须在告警里说清楚会缺图"""
        s = WechatStub(uploadimg={"errcode": 40007, "errmsg": "invalid media_id"})
        monkeypatch.setattr("urllib.request.urlopen", s)
        f = write('<section><img src="https://cdn.example.com/a.png"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert r.success is True, "草稿仍应推送成功"
        assert r.images_transferred == 0
        assert any("缺失" in w and "40007" in w for w in r.warnings)
        content = json.loads(s.only("/draft/add")[0]["body"])["articles"][0]["content"]
        assert "cdn.example.com" in content, "失败时保留原 src，不写坏数据"

    def test_unreadable_image_warns_with_reason(self, env, stub, tmp_path):
        f = write('<section><img src="./not-exist.png"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert r.success is True
        assert r.images_transferred == 0
        assert any("不存在" in w and "缺失" in w for w in r.warnings)

    def test_download_failure_reason_is_reported(self, monkeypatch, env, tmp_path):
        """回归：告警里必须说清是 404 / 超时 / 格式不对，只写「读取失败」没法排查"""
        import urllib.error

        class NotFoundStub(WechatStub):
            def __call__(self, req, timeout=None):
                if "/cgi-bin/" in req.full_url:
                    return super().__call__(req, timeout)
                raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

        s = NotFoundStub()
        monkeypatch.setattr("urllib.request.urlopen", s)
        f = write('<section><img src="https://cdn.example.com/gone.png"></section>', tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert r.success is True
        assert any("404" in w and "缺失" in w for w in r.warnings)


class TestThumbUpload:
    def test_local_thumb_is_uploaded_for_media_id(self, env, stub, tmp_path):
        thumb = tmp_path / "cover.png"
        thumb.write_bytes(png_bytes())
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_image=thumb)
        assert r.success is True
        mat = stub.only("/material/add_material")
        assert len(mat) == 1
        assert "type=image" in mat[0]["url"]
        assert png_bytes()[:8] in mat[0]["body"], "封面字节要真的放进 multipart"
        art = json.loads(stub.only("/draft/add")[0]["body"])["articles"][0]
        assert art["thumb_media_id"] == "THUMB_MEDIA_ID"

    def test_explicit_thumb_media_id_skips_upload(self, env, stub, tmp_path):
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        Publisher().publish_to_wechat(f, title="t", thumb_media_id="GIVEN_ID", thumb_image=tmp_path / "x.png")
        assert stub.only("/material/add_material") == []

    def test_missing_thumb_file_fails_clearly(self, env, stub, tmp_path):
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_image=tmp_path / "nope.png")
        assert r.success is False
        assert "封面图" in r.message
        assert stub.only("/draft/add") == []


class TestErrorSurfacing:
    def test_token_error_including_ip_hint_is_shown(self, env, monkeypatch, tmp_path):
        s = WechatStub(token_ok=False)
        monkeypatch.setattr("urllib.request.urlopen", s)
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert r.success is False
        assert "40164" in r.message and "whitelist" in r.message
        assert s.only("/draft/add") == []

    def test_draft_api_error_is_surfaced(self, monkeypatch, env, tmp_path):
        class ErrStub(WechatStub):
            def __call__(self, req, timeout=None):
                url = req.full_url
                self.calls.append({"url": url, "body": getattr(req, "data", None)})
                if "/cgi-bin/token" in url:
                    return FakeResp(json.dumps({"access_token": "TOK"}).encode())
                return FakeResp(json.dumps({"errcode": 40007, "errmsg": "invalid media_id"}).encode())

        s = ErrStub()
        monkeypatch.setattr("urllib.request.urlopen", s)
        f = write("<section><p>x</p></section>", tmp_path / "a.html")
        r = Publisher().publish_to_wechat(f, title="t", thumb_media_id="T")
        assert r.success is False
        assert "40007" in r.message
