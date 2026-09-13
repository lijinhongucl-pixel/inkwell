"""封面设计顾问

高转化视觉规律知识库：
  - 分析文章主题/类型，推荐最适合的封面设计方案
  - 内置 6 种高转化封面模式（大标题型、数据对比型、截图证据型等）
  - 不依赖外部 API，纯静态知识库 + 规则匹配

用法：
    advisor = CoverAdvisor()
    advice = advisor.advise(topic="Docker 优化", article_type="tutorial")
    print(advice.recommendation)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CoverAdvice:
    """封面设计建议"""

    pattern_id: str
    pattern_name: str
    description: str
    color_suggestion: str
    layout_hint: str
    title_tips: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)


# ============================================================
# 高转化封面模式知识库
# ============================================================
COVER_PATTERNS: dict[str, CoverAdvice] = {
    "big-title": CoverAdvice(
        pattern_id="big-title",
        pattern_name="大标题冲击型",
        description=("标题占封面 50% 以上面积，用大字号 + 强对比色制造视觉冲击。适合干货教程、工具推荐类内容。"),
        color_suggestion="深色背景 + 白/亮色标题（黑底白字反差最大）",
        layout_hint="标题居左对齐占上半部分，下半留白或放小标签",
        title_tips=[
            "标题控制在 15 字以内",
            "核心关键词加粗或换色",
            "可用数字开头（如「3 个技巧」「5 倍提速」）",
        ],
        avoid=["标题超过 20 字", "标题与背景对比度不足"],
    ),
    "data-comparison": CoverAdvice(
        pattern_id="data-comparison",
        pattern_name="数据对比型",
        description=("用数字、柱状图或对比表格作为封面主体。适合测评、横评、性能对比类内容。"),
        color_suggestion="浅色背景 + 深色数据元素（突出数字可读性）",
        layout_hint="核心数据居中大字号，辅助数据小字号排列",
        title_tips=[
            "挑最大的数字做封面锚点",
            "单位要清晰（ms、MB、%）",
            "对比对象用不同颜色区分",
        ],
        avoid=["数据太多看不清重点", "数字没有单位"],
    ),
    "screenshot-evidence": CoverAdvice(
        pattern_id="screenshot-evidence",
        pattern_name="截图证据型",
        description=("以产品截图、代码片段、界面截图作为封面核心元素。适合工具实操、代码教程、产品评测。"),
        color_suggestion="截图原色 + 深色边框/阴影提升层次",
        layout_hint="截图占 60-70% 面积，标题在顶部或底部叠加",
        title_tips=[
            "截图要有明确视觉焦点",
            "可加红框/箭头标注重点",
            "模糊敏感信息",
        ],
        avoid=["截图模糊", "截图无标注看不出重点"],
    ),
    "question-hook": CoverAdvice(
        pattern_id="question-hook",
        pattern_name="提问钩子型",
        description=("用一个问题或悬念句作为封面主体。适合观点分析、趋势解读、深度思考类内容。"),
        color_suggestion="简约浅色背景 + 深色文字（让问题本身成为焦点）",
        layout_hint="问句居中，字号中等但留白充足",
        title_tips=[
            "问题要直击痛点",
            "不超过 20 字",
            "可用「？」增大制造悬念感",
        ],
        avoid=["问题太长", "问题不够刺激（如「什么是 Docker？」不如「为什么 Docker 让你的部署快 10 倍？」）"],
    ),
    "list-countdown": CoverAdvice(
        pattern_id="list-countdown",
        pattern_name="清单/盘点型",
        description=("以编号列表或盘点形式作为封面结构。适合合集、盘点、Top N、工具箱类内容。"),
        color_suggestion="分条用不同色块或编号徽标",
        layout_hint="竖向列表排列，每条带编号徽标",
        title_tips=[
            "明确总数（如「10 个工具」「Top 5」）",
            "每条配简短关键词",
            "封面只展示前 3-4 条制造好奇",
        ],
        avoid=["所有条目都放上封面（太多看不清）", "编号无视觉差异"],
    ),
    "before-after": CoverAdvice(
        pattern_id="before-after",
        pattern_name="前后对比型",
        description=("用 Before / After 对比展示效果。适合优化技巧、改造教程、性能提升类内容。"),
        color_suggestion="左侧灰暗（Before） + 右侧明亮（After）",
        layout_hint="左右或上下分割，中间箭头或分割线",
        title_tips=[
            "差异要明显",
            "标注关键数据变化（如「950MB → 120MB」）",
            "箭头引导视线方向",
        ],
        avoid=["前后差异不明显", "缺少数据对比"],
    ),
}

# ============================================================
# 文章类型 → 封面模式推荐映射
# ============================================================
TYPE_TO_PATTERN: dict[str, list[str]] = {
    "tutorial": ["big-title", "screenshot-evidence", "before-after"],
    "review": ["data-comparison", "screenshot-evidence"],
    "analysis": ["question-hook", "data-comparison"],
    "opinion": ["question-hook", "big-title"],
    "list": ["list-countdown", "big-title"],
    "comparison": ["data-comparison", "before-after"],
    "general": ["big-title", "question-hook"],
}

# 关键词 → 封面模式信号词
KEYWORD_SIGNALS: dict[str, list[str]] = {
    "big-title": ["工具", "技巧", "教程", "入门", "指南", "推荐"],
    "data-comparison": ["对比", "评测", "横评", "vs", "PK", "最好"],
    "screenshot-evidence": ["实操", "演示", "步骤", "截图", "界面"],
    "question-hook": ["为什么", "如何", "怎样", "到底", "真的"],
    "list-countdown": ["Top", "盘点", "合集", "清单", "N个", "10大"],
    "before-after": ["优化", "提速", "瘦身", "改造", "升级", "迁移"],
}


class CoverAdvisor:
    """封面设计顾问

    根据文章主题和类型推荐最合适的封面设计方案。

    用法：
        advisor = CoverAdvisor()
        advice = advisor.advise(topic="Docker 镜像优化", article_type="tutorial")
        print(advice)
    """

    def advise(
        self,
        topic: str,
        article_type: str = "general",
        content_text: str = "",
    ) -> CoverAdvice:
        """分析主题和类型，返回封面设计建议

        Args:
            topic:        文章主题/标题
            article_type: tutorial/review/analysis/opinion/list/comparison/general
            content_text: 可选，文章正文片段用于关键词补充匹配
        """
        # 1. 类型直接映射
        type_patterns = TYPE_TO_PATTERN.get(article_type, TYPE_TO_PATTERN["general"])

        # 2. 关键词信号匹配
        combined = f"{topic} {content_text}".lower()
        signal_scores: dict[str, int] = {}

        for pattern_id, signals in KEYWORD_SIGNALS.items():
            score = 0
            for sig in signals:
                if sig.lower() in combined:
                    score += 1
            signal_scores[pattern_id] = score

        # 3. 综合：类型映射优先 + 关键词加分
        ranked: list[tuple[str, int]] = []
        for pid in type_patterns:
            base = (len(type_patterns) - type_patterns.index(pid)) * 2  # 类型排名权重
            ranked.append((pid, base + signal_scores.get(pid, 0)))

        # 如果关键词信号有类型映射外的强信号，也纳入
        for pid, score in signal_scores.items():
            if score > 0 and pid not in type_patterns:
                ranked.append((pid, score))

        ranked.sort(key=lambda x: x[1], reverse=True)

        best_id = ranked[0][0] if ranked else "big-title"
        return COVER_PATTERNS[best_id]

    def advise_multi(
        self,
        topic: str,
        article_type: str = "general",
        content_text: str = "",
        top_n: int = 3,
    ) -> list[CoverAdvice]:
        """返回多个备选建议供用户选择"""
        type_patterns = TYPE_TO_PATTERN.get(article_type, TYPE_TO_PATTERN["general"])
        combined = f"{topic} {content_text}".lower()

        ranked: list[tuple[str, int]] = []
        for pid in type_patterns:
            base = (len(type_patterns) - type_patterns.index(pid)) * 2
            kw_score = sum(1 for sig in KEYWORD_SIGNALS.get(pid, []) if sig.lower() in combined)
            ranked.append((pid, base + kw_score))

        # 用所有模式兜底，确保能凑够 top_n
        for pid in COVER_PATTERNS:
            if pid not in [r[0] for r in ranked]:
                kw_score = sum(1 for sig in KEYWORD_SIGNALS.get(pid, []) if sig.lower() in combined)
                ranked.append((pid, kw_score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return [COVER_PATTERNS[pid] for pid, _ in ranked[:top_n]]

    @staticmethod
    def list_patterns() -> list[dict]:
        """列出所有封面模式"""
        return [
            {"id": p.pattern_id, "name": p.pattern_name, "desc": p.description[:60]} for p in COVER_PATTERNS.values()
        ]
