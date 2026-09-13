"""Markdown 草稿生成器

安装到 AI Agent 后，Agent 可以根据主题自动生成结构化的 Markdown 草稿，
然后直接喂给流水线排版发布。

设计理念：
- 不依赖外部 AI API，用模板 + 结构化骨架生成初稿
- Agent 拿到草稿后可以自行润色、补充内容
- 支持 5 种文章风格，每种有专属章节骨架
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ArticleStyle:
    """文章风格定义"""

    id: str
    name: str
    sections: list[str]  # 章节标题模板
    intro: str  # 引言段模板
    tone: str  # 语气描述


# ============================================================
# 5 种文章风格的章节骨架
# ============================================================
STYLES: dict[str, ArticleStyle] = {
    "tutorial": ArticleStyle(
        id="tutorial",
        name="教程",
        sections=[
            "背景介绍",
            "环境准备",
            "核心步骤",
            "进阶用法",
            "常见问题（FAQ）",
            "总结",
        ],
        intro="这篇讲清楚 **{topic}** 怎么用，从零开始，每一步都能跟着做。",
        tone="操作指南，每步给命令和截图占位",
    ),
    "review": ArticleStyle(
        id="review",
        name="测评",
        sections=[
            "结论先行",
            "核心功能对比",
            "适用场景",
            "谨慎场景",
            "FAQ",
            "信源与免责声明",
        ],
        intro="关于 **{topic}**，先说结论，再展开细节。",
        tone="客观对比，表格驱动，结论前置",
    ),
    "analysis": ArticleStyle(
        id="analysis",
        name="深度分析",
        sections=[
            "问题定义",
            "现状梳理",
            "核心论点",
            "数据支撑",
            "趋势判断",
            "总结与展望",
        ],
        intro="本文深度拆解 **{topic}**，从底层逻辑到上层应用逐层分析。",
        tone="逻辑推演，数据论证，结构化",
    ),
    "opinion": ArticleStyle(
        id="opinion",
        name="观点",
        sections=[
            "核心观点",
            "为什么这么说",
            "反面意见",
            "我的立场",
            "留给你的思考",
        ],
        intro="关于 **{topic}**，我有不一样的看法。",
        tone="第一人称，有态度，引发讨论",
    ),
    "general": ArticleStyle(
        id="general",
        name="通用",
        sections=[
            "引入",
            "主要内容",
            "要点总结",
            "后续展望",
        ],
        intro="今天聊一聊 **{topic}**。",
        tone="自然口语，结构清晰",
    ),
}


class DraftGenerator:
    """Markdown 草稿生成器

    用法：
        gen = DraftGenerator()
        md = gen.generate("Docker 多阶段构建", style="tutorial")

    带搜索自动填充：
        gen = DraftGenerator()
        md = gen.generate_with_search("Docker 优化", style="tutorial", search_source="github")
    """

    def generate(self, topic: str, style: str = "general", outline_only: bool = False) -> str:
        """根据主题和风格生成 Markdown 草稿

        Args:
            topic:       文章主题/标题
            style:       tutorial/review/analysis/opinion/general
            outline_only: 只生成大纲不展开占位段落
        """
        if style not in STYLES:
            raise ValueError(f"未知风格: {style}，可选: {list(STYLES)}")
        s = STYLES[style]

        lines: list[str] = []
        lines.append(f"# {topic}\n")
        intro = s.intro.format(topic=topic)
        lines.append(f"> {intro}\n")

        if outline_only:
            lines.append("## 大纲\n")
            for i, section in enumerate(s.sections, 1):
                lines.append(f"{i}. {section}")
            lines.append("")
        else:
            for i, section in enumerate(s.sections, 1):
                lines.append(f"## {section}\n")
                # 占位符写成 HTML 注释：写作者在源文件里能看到，
                # 排版后会被 MarkdownProcessor 整段剥离，不会漏进正文
                lines.append(f"<!-- TODO: 在此填写「{section}」的内容 -->\n")
            lines.append("---\n")
            lines.append("> 本文仅供参考，具体信息请以官方文档为准。\n")

        return "\n".join(lines)

    def generate_with_search(
        self,
        topic: str,
        style: str = "general",
        search_source: str = "github",
        search_limit: int = 5,
        outline_only: bool = False,
        fallback_queries: list[str] | None = None,
    ) -> str:
        """带搜索结果的增强草稿生成

        搜索与主题相关的 GitHub 项目/参考素材，
        自动填充到「参考素材」章节和数据段落中，
        替代纯粹的 TODO 占位符。

        中文主题先用原文搜索 GitHub（可能返回少量结果），
        如果结果为空，自动用 fallback_queries 或提取的关键词重试。

        Args:
            topic:            文章主题
            style:            文章风格
            search_source:    github / web / custom
            search_limit:     搜索结果数量
            outline_only:     只生成大纲
            fallback_queries: 自定义降级查询列表
        """
        from .searcher import ContentSearcher

        # 先生成基础草稿
        base_md = self.generate(topic, style=style, outline_only=outline_only)

        # 搜索相关素材
        try:
            searcher = ContentSearcher()
            results = searcher.search(
                query=topic,
                source=search_source,
                limit=search_limit,
            )
        except Exception:
            results = []

        # GitHub 对纯中文查询支持差，降级策略：
        # 1. 提取技术关键词重试
        # 2. 使用 fallback_queries
        if not results and search_source == "github":
            queries = fallback_queries or self._extract_keywords(topic)
            for q in queries:
                try:
                    results = searcher.search(
                        query=q,
                        source=search_source,
                        limit=search_limit,
                    )
                    if results:
                        break
                except Exception:
                    continue

        if not results:
            # 最终降级：在草稿里加一句说明
            lines = base_md.split("\n")
            lines.insert(-2, f"\n> 未找到「{topic}」的相关参考素材，建议手动搜索补充。\n")
            return "\n".join(lines)

        # 构建「参考素材」章节
        ref_lines = [
            "\n## 参考素材（自动搜索）\n",
            f"> 以下素材通过搜索「{topic}」自动获取，可作为文章引用和参考。\n",
            "",
        ]
        for i, r in enumerate(results, 1):
            star_str = f"（⭐{r.stars}）" if r.stars else ""
            lang_str = f" `{r.language}`" if r.language else ""
            ref_lines.append(f"### {i}. [{r.title}]({r.url}){star_str}{lang_str}\n")
            if r.description:
                ref_lines.append(f"{r.description}\n")
            ref_lines.append("")

        ref_lines.append("---\n")

        # 把参考素材章节插入到「---」信源免责声明之前
        ref_block = "\n".join(ref_lines)
        if "\n---\n" in base_md:
            base_md = base_md.rsplit("\n---\n", 1)[0] + "\n" + ref_block
        else:
            base_md += "\n" + ref_block

        return base_md

    # ---------- 关键词提取 ----------
    @staticmethod
    def _extract_keywords(topic: str) -> list[str]:
        """从中文主题中提取技术关键词用于英文搜索降级

        常见中文技术词 → 英文搜索词映射，
        如果没有命中映射，就把整个主题作为 fallback。
        """
        # 中文技术词映射表（可扩展）
        TOPIC_MAP: dict[str, str] = {
            "Docker": "Docker",
            "镜像": "container image",
            "容器": "container",
            "多阶段": "multi-stage build",
            "优化": "optimization",
            "瘦身": "size reduction",
            "CI/CD": "CI CD pipeline",
            "部署": "deployment",
            "Kubernetes": "Kubernetes",
            "K8s": "Kubernetes",
            "微服务": "microservice",
            "Python": "Python",
            "React": "React",
            "Vue": "Vue.js",
            "AI": "AI agent",
            "大模型": "LLM large language model",
            "工具": "tool",
            "教程": "tutorial",
            "测评": "review benchmark",
        }
        keywords: list[str] = []
        for cn, en in TOPIC_MAP.items():
            if cn.lower() in topic.lower():
                keywords.append(en)
        # 如果没命中任何关键词，用原主题做最后一次尝试
        if not keywords:
            keywords.append(topic)
        return keywords

    @staticmethod
    def list_styles() -> list[dict[str, str]]:
        """返回所有可用风格"""
        return [{"id": s.id, "name": s.name, "tone": s.tone} for s in STYLES.values()]
