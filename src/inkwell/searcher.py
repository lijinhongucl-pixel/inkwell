"""内容搜索模块

帮助创作者发现选题灵感、参考素材、热门项目。
设计为可扩展的适配器模式：内置 GitHub trending 和 web 搜索，
用户可通过 --backend 自定义搜索后端。
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """单条搜索结果"""

    title: str
    url: str
    source: str  # github / web / custom
    description: str = ""
    stars: int | None = None  # GitHub 专用
    language: str = ""  # GitHub 专用
    extra: dict = field(default_factory=dict)

    def to_markdown_row(self) -> str:
        """转成 Markdown 表格行，方便插入文章做引用素材"""
        star_str = f"⭐{self.stars}" if self.stars else ""
        lang_str = f" `{self.language}`" if self.language else ""
        return f"| [{self.title}]({self.url}){lang_str} | {star_str} | {self.description[:60]} |"

    def __str__(self) -> str:
        parts = [f"[{self.title}]({self.url})"]
        if self.stars:
            parts.append(f"⭐{self.stars}")
        if self.language:
            parts.append(f"`{self.language}`")
        if self.description:
            parts.append(f"— {self.description[:80]}")
        return " ".join(parts)


class ContentSearcher:
    """内容搜索入口

    用法：
        searcher = ContentSearcher()
        results = searcher.search("AI agent", source="github", limit=10)
        for r in results:
            print(r)
    """

    def search(
        self,
        query: str,
        source: str = "github",
        limit: int = 10,
        backend: str | None = None,
    ) -> list[SearchResult]:
        """执行搜索，返回结构化结果列表

        Args:
            query:   搜索关键词
            source:  github / web / custom
            limit:   最大结果数
            backend: 自定义搜索 API 地址（覆盖 source）
        """
        if backend:
            return self._search_custom(query, backend, limit)
        if source == "github":
            return self._search_github(query, limit)
        if source == "web":
            return self._search_web(query, limit)
        raise ValueError(f"不支持的 source: {source}（可选: github / web / custom）")

    # ---------- GitHub 搜索 ----------
    def _search_github(self, query: str, limit: int) -> list[SearchResult]:
        """搜索 GitHub 仓库，返回热门项目"""
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
            {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": min(limit, 30),
            }
        )
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "inkwell",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception:
            return []

        results: list[SearchResult] = []
        for item in data.get("items", [])[:limit]:
            results.append(
                SearchResult(
                    title=item["full_name"],
                    url=item["html_url"],
                    source="github",
                    description=item.get("description", ""),
                    stars=item.get("stargazers_count"),
                    language=item.get("language") or "",
                    extra={
                        "forks": item.get("forks_count"),
                        "topics": item.get("topics", []),
                    },
                )
            )
        return results

    # ---------- Web 搜索（公共搜索引擎 API） ----------
    def _search_web(self, query: str, limit: int) -> list[SearchResult]:
        """通用 web 搜索适配器

        默认不绑定特定搜索引擎 API（需要用户提供自己的 backend），
        此方法返回提示性结果告知用户如何配置。
        """
        # 没有自定义 backend 时返回结构化提示
        return [
            SearchResult(
                title="Web 搜索需配置自定义后端",
                url="",
                source="web",
                description=(
                    "使用 --backend 'https://your-search-api.com/search' "
                    "指定搜索 API 地址。API 需返回 JSON："
                    '[{"title":"...", "url":"...", "description":"..."}]'
                ),
            )
        ]

    # ---------- 自定义后端 ----------
    def _search_custom(self, query: str, backend: str, limit: int) -> list[SearchResult]:
        """调用用户自定义搜索 API

        API 约定：
        - GET 请求，query 参数名 `q`，limit 参数名 `limit`
        - 返回 JSON 数组，每项含 title / url / description 字段
        """
        url = f"{backend}?" + urllib.parse.urlencode({"q": query, "limit": limit})
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "inkwell",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception:
            return []

        if isinstance(data, dict):
            data = data.get("results", data.get("items", []))

        results: list[SearchResult] = []
        for item in data[:limit] if isinstance(data, list) else []:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source="custom",
                    description=item.get("description", ""),
                )
            )
        return results

    # ---------- 输出格式化 ----------
    @staticmethod
    def to_markdown(results: list[SearchResult], title: str = "搜索结果") -> str:
        """把搜索结果格式化为 Markdown 表格，可直接插入文章"""
        if not results:
            return f"## {title}\n\n无结果。\n"

        lines = [f"## {title}\n"]
        has_stars = any(r.stars for r in results)
        if has_stars:
            lines.append("| 项目 | Stars | 简介 |")
            lines.append("|------|-------|------|")
            for r in results:
                lines.append(r.to_markdown_row())
        else:
            lines.append("| 标题 | 来源 | 简介 |")
            lines.append("|------|------|------|")
            for r in results:
                lines.append(f"| [{r.title}]({r.url}) | {r.source} | {r.description[:60]} |")
        return "\n".join(lines) + "\n"
