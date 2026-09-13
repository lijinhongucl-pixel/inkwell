"""CLI 装配层测试

历史教训（2026-09-13 陌生用户验收发现）：
image_proc 的单元测试是全绿的 —— 压缩、上传、失败降级都覆盖了；但 cli.py 构造
PipelineConfig 时漏传 github_repo 与 cdn_base，导致 CLI 路径下 CDN 外链 100% 失效，
发布版与本地版字节完全相同。

单元测试测不到「层与层之间的缝」。本文件专门锁死「CLI 参数 → PipelineConfig」
这一段装配，避免同类缺陷再次溜过。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from inkwell import cli
from inkwell.core import PipelineConfig, PipelineResult


@pytest.fixture
def captured_config(monkeypatch) -> dict:
    """把 Pipeline 换成捕获器，拿到 cmd_run 实际构造出的 PipelineConfig"""
    box: dict = {}

    class FakePipeline:
        def __init__(self, config: PipelineConfig) -> None:
            box["config"] = config

        def run(self) -> PipelineResult:
            return PipelineResult(publish_html=Path("/tmp/inkwell-fake.html"))

    monkeypatch.setattr(cli, "Pipeline", FakePipeline)
    return box


class TestRunCdnWiring:
    def test_repo_and_cdn_base_reach_config(self, captured_config):
        args = cli.build_parser().parse_args(
            [
                "run",
                "article.md",
                "--github-repo",
                "me/image-repo",
                "--cdn-base",
                "https://cdn.jsdelivr.net/gh/me/image-repo@main",
            ]
        )
        assert cli.cmd_run(args) == 0
        cfg = captured_config["config"]
        assert cfg.github_repo == "me/image-repo"
        assert cfg.cdn_base == "https://cdn.jsdelivr.net/gh/me/image-repo@main"

    def test_defaults_are_empty(self, captured_config, monkeypatch):
        monkeypatch.delenv("INKWELL_GITHUB_REPO", raising=False)
        monkeypatch.delenv("INKWELL_CDN_BASE", raising=False)
        args = cli.build_parser().parse_args(["run", "article.md"])
        cli.cmd_run(args)
        cfg = captured_config["config"]
        assert cfg.github_repo == ""
        assert cfg.cdn_base == ""

    def test_env_var_fallback(self, monkeypatch):
        monkeypatch.setenv("INKWELL_GITHUB_REPO", "env/image-repo")
        monkeypatch.setenv("INKWELL_CDN_BASE", "https://cdn.env/base")
        args = cli.build_parser().parse_args(["run", "article.md"])
        assert args.github_repo == "env/image-repo"
        assert args.cdn_base == "https://cdn.env/base"

    def test_cli_flag_overrides_env(self, monkeypatch):
        monkeypatch.setenv("INKWELL_GITHUB_REPO", "env/image-repo")
        args = cli.build_parser().parse_args(["run", "article.md", "--github-repo", "flag/image-repo"])
        assert args.github_repo == "flag/image-repo"

    def test_no_upload_drops_token(self, captured_config, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
        args = cli.build_parser().parse_args(["run", "article.md", "--no-upload"])
        cli.cmd_run(args)
        assert captured_config["config"].github_token is None


class TestRunExternalImageWiring:
    """外链图内嵌开关必须能从 CLI 走到 PipelineConfig（装配层的缝最容易漏）"""

    def test_embed_external_on_by_default(self, captured_config):
        args = cli.build_parser().parse_args(["run", "article.md"])
        cli.cmd_run(args)
        assert captured_config["config"].embed_external is True

    def test_no_embed_external_flag_reaches_config(self, captured_config):
        args = cli.build_parser().parse_args(["run", "article.md", "--no-embed-external"])
        cli.cmd_run(args)
        assert captured_config["config"].embed_external is False
