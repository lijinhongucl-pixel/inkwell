"""敏感词 / 合规检测

扫描中文内容中的潜在合规风险词，给出替换建议。

三类检测规则：
1. **广告法极限词**：「最」「第一」「国家级」「顶级」等
   《广告法》明令禁止的绝对化用语
2. **平台高频违规词**：「免费」「秒杀」「包过」「加我微信」等
   微信/小红书社区常见拦截词
3. **通用敏感词**：涉及政治、医疗、金融等高风险领域的
   需谨慎使用的表述

使用方式：
    checker = WordChecker()
    report = checker.check("文章内容")
    for hit in report.hits:
        print(f"{hit.word} → 建议: {hit.suggestion}")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ============================================================
# 敏感词库
# ============================================================

# 广告法极限词（绝对化用语）
AD_LAW_WORDS: dict[str, str] = {
    "最": "较为突出的",
    "最好": "优质的",
    "最大": "较大的",
    "最小": "较小的",
    "最高": "较高的",
    "最低": "较低的",
    "最快": "较快的",
    "最新": "较新的",
    "最优": "较优的",
    "最先进": "先进的",
    "最流行": "流行的",
    "最受欢迎": "广受好评",
    "第一": "领先",
    "第一品牌": "知名品牌",
    "第一名": "名列前茅",
    "唯一": "少见的",
    "唯一 choice": "优秀选择",
    "国家级": "行业级",
    "世界级": "高水平",
    "顶级": "高端",
    "极品": "优质",
    "绝佳": "出色",
    "完美": "完善",
    "万能": "多功能",
    "百分百": "很大程度上",
    "100%": "很大程度上",
    "绝无仅有": "罕见",
    "史无前例": "少有",
    "空前": "罕见",
    "绝版": "限量",
    "巅峰": "高水平",
    "巅峰之作": "代表作品",
    "之王": "佼佼者",
    "之最": "领先水平",
    "遥遥领先": "领先",
    "遥遥最先": "领先",
}

# 平台高频违规词
PLATFORM_VIOLATION_WORDS: dict[str, str] = {
    "免费领取": "领取福利",
    "免费送": "福利放送",
    "秒杀": "限时优惠",
    "抢购": "选购",
    "包过": "系统辅导",
    "包就业": "推荐就业",
    "加我微信": "联系作者",
    "加微信": "联系作者",
    "加群": "加入讨论",
    "扫码加我": "联系作者",
    "代理加盟": "合作",
    "刷单": "推广",
    "刷量": "推广",
    "买粉": "增长粉丝",
    "卖号": "转让",
    "返现": "回馈",
    "传销": "分销",
    "赌博": "博彩（需谨慎）",
    "代购": "采购",
    "朋友圈截图": "分享截图",
    "点赞转发": "支持分享",
    "不转不是中国人": "（建议删除）",
}

# 通用敏感词（需人工复核）
SENSITIVE_WORDS: dict[str, str] = {
    "毛主席": "（使用全名+职务）",
    "习近平": "（按官方规范引用）",
    "国家领导人": "有关负责人",
    "政府": "（视语境，可用「相关部门」）",
    "中共": "（视语境，可用「执政党」）",
    "革命": "变革",
    "推翻": "改变",
    "政权": "管理层",
    "独裁": "集中决策",
    "民主": "公开讨论",
    "自由": "灵活",
    "游行": "集体活动",
    "示威": "表达诉求",
    "罢工": "停工",
    "维权": "保护权益",
    "上访": "反映情况",
    "反腐": "廉政建设",
    "贪腐": "不当行为",
    "疫苗": "（医疗内容需谨慎）",
    "癌症": "重大疾病",
    "肿瘤": "健康问题",
    "艾滋": "传染病",
    "精神病": "心理健康问题",
    "自杀": "轻生（需加求助热线）",
    "抑郁症": "情绪障碍",
    "毒品": "违禁品",
    "色情": "低俗内容",
    "暴力": "过激行为",
    "恐怖": "极端事件",
}

# 需要额外关注的组合词（正则模式）
REGEX_PATTERNS: list[tuple[str, str, str]] = [
    (r"全国\s*第一", "全国领先", "广告法极限词"),
    (r"全球\s*第一", "全球领先", "广告法极限词"),
    (r"史上\s*最", "罕见的", "广告法极限词"),
    (r"没有\s*之一", "顶尖水平", "广告法极限词"),
    (r" [\d.]+\s*亿\s*用户", "大量用户", "数据需核实"),
]


@dataclass
class WordHit:
    """单个敏感词命中"""

    word: str  # 原始词
    suggestion: str  # 替换建议
    category: str  # 分类：ad-law / platform / sensitive / regex
    line_num: int  # 行号
    context: str  # 上下文片段（前后各 15 字符）

    def __str__(self) -> str:
        return (
            f"[{self.category}] L{self.line_num} "
            f"「{self.word}」 → 建议替换为「{self.suggestion}」"
            f"\n  上下文: ...{self.context}..."
        )


@dataclass
class WordCheckReport:
    """敏感词检测报告"""

    hits: list[WordHit] = field(default_factory=list)
    total_scanned: int = 0

    @property
    def is_clean(self) -> bool:
        return len(self.hits) == 0

    @property
    def risk_level(self) -> str:
        """整体风险等级"""
        n = len(self.hits)
        if n == 0:
            return "PASS"
        if n <= 3:
            return "LOW"
        if n <= 8:
            return "MEDIUM"
        return "HIGH"

    def summary(self) -> str:
        lines = [
            "敏感词检测报告",
            f"{'=' * 50}",
            f"扫描字符数: {self.total_scanned}",
            f"命中数: {len(self.hits)}",
            f"风险等级: {self.risk_level}",
            f"{'=' * 50}",
        ]
        if self.is_clean:
            lines.append("未发现敏感词，可以放心发布。")
        else:
            # 按分类分组
            by_cat: dict[str, list[WordHit]] = {}
            for hit in self.hits:
                by_cat.setdefault(hit.category, []).append(hit)

            cat_names = {
                "ad-law": "广告法极限词（高风险）",
                "platform": "平台违规词（中风险）",
                "sensitive": "通用敏感词（需人工复核）",
                "regex": "组合敏感模式",
            }

            for cat, hits in by_cat.items():
                lines.append(f"\n【{cat_names.get(cat, cat)}】{len(hits)} 条")
                for h in hits:
                    lines.append(f"  {h}")

        return "\n".join(lines)


class WordChecker:
    """敏感词 / 合规检测器

    用法：
        checker = WordChecker()
        report = checker.check(markdown_text)
        print(report.summary())
    """

    def __init__(
        self,
        *,
        check_ad_law: bool = True,
        check_platform: bool = True,
        check_sensitive: bool = True,
        check_regex: bool = True,
    ) -> None:
        self.check_ad_law = check_ad_law
        self.check_platform = check_platform
        self.check_sensitive = check_sensitive
        self.check_regex = check_regex

    def check(self, text: str) -> WordCheckReport:
        """扫描文本，返回检测报告"""
        report = WordCheckReport(total_scanned=len(text))
        lines = text.splitlines()
        in_code = False

        for line_num, line in enumerate(lines, start=1):
            # 代码块状态机
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue

            # 广告法极限词
            if self.check_ad_law:
                for word, suggestion in AD_LAW_WORDS.items():
                    if word in line:
                        report.hits.append(
                            self._make_hit(
                                word,
                                suggestion,
                                "ad-law",
                                line_num,
                                line,
                            )
                        )

            # 平台违规词
            if self.check_platform:
                for word, suggestion in PLATFORM_VIOLATION_WORDS.items():
                    if word in line:
                        report.hits.append(
                            self._make_hit(
                                word,
                                suggestion,
                                "platform",
                                line_num,
                                line,
                            )
                        )

            # 通用敏感词
            if self.check_sensitive:
                for word, suggestion in SENSITIVE_WORDS.items():
                    if word in line:
                        report.hits.append(
                            self._make_hit(
                                word,
                                suggestion,
                                "sensitive",
                                line_num,
                                line,
                            )
                        )

            # 正则组合词
            if self.check_regex:
                for pattern, suggestion, cat in REGEX_PATTERNS:
                    m = re.search(pattern, line)
                    if m:
                        report.hits.append(
                            self._make_hit(
                                m.group(),
                                suggestion,
                                "regex",
                                line_num,
                                line,
                            )
                        )

        return report

    @staticmethod
    def _make_hit(
        word: str,
        suggestion: str,
        cat: str,
        line_num: int,
        line: str,
    ) -> WordHit:
        """构造命中记录，提取上下文"""
        idx = line.find(word)
        if idx >= 0:
            start = max(0, idx - 15)
            end = min(len(line), idx + len(word) + 15)
            context = line[start:end]
        else:
            context = line[:30]
        return WordHit(
            word=word,
            suggestion=suggestion,
            category=cat,
            line_num=line_num,
            context=context,
        )
