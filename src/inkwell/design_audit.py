"""设计质量三门审计

三道质量门，用于审查一切视觉产出：
  Gate 1 — 主题与载体合理性：形式是否符合读者动作？
  Gate 2 — 基准对照：视觉密度是否不差于人工参考？
  Gate 3 — 可编辑交付：产出是否可二次编辑和审查？

用法：
    auditor = DesignAuditor()
    report = auditor.audit_html_cover(html_path)
    report = auditor.audit_html_article(html_path)
    for gate_result in report.gates:
        print(gate_result)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class GateStatus(Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class GateResult:
    """单道门的审计结果"""

    gate: str  # Gate 1 / Gate 2 / Gate 3
    name: str  # 门名称
    status: GateStatus
    checks_passed: int = 0
    checks_total: int = 0
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status != GateStatus.FAIL

    def __str__(self) -> str:
        icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[self.status.value]
        head = f"[{icon}] {self.gate} {self.name} ({self.checks_passed}/{self.checks_total})"
        if self.issues:
            head += "\n" + "\n".join(f"  ! {i}" for i in self.issues)
        if self.notes:
            head += "\n" + "\n".join(f"  - {n}" for n in self.notes)
        return head


@dataclass
class AuditReport:
    """完整审计报告"""

    target: str
    gates: list[GateResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """无 FAIL 即视为通过（WARN 不阻断发布）"""
        return all(g.passed for g in self.gates)

    @property
    def has_warning(self) -> bool:
        return any(g.status == GateStatus.WARN for g in self.gates)

    def summary(self) -> str:
        lines = [f"=== Design Audit: {self.target} ==="]
        for g in self.gates:
            lines.append(str(g))
        fails = [g for g in self.gates if g.status == GateStatus.FAIL]
        warns = [g for g in self.gates if g.status == GateStatus.WARN]
        if fails:
            lines.append(f"\n{len(fails)} 道门未通过，需修复后重新审计。")
        elif warns:
            lines.append(f"\n{len(warns)} 道门有警告，可发布但建议优化。")
        else:
            lines.append("\n所有门通过。")
        return "\n".join(lines)


class DesignAuditor:
    """三门质量审计器

    审计一切 HTML 产出（封面、文章、社交卡片），
    确保符合 Victor Design System 的质量标准。
    """

    # ============================================================
    # Gate 1: 主题与载体合理性
    # ============================================================
    GATE1_RULES = {
        "has_title": {
            "check": re.compile(r"<h1[^>]*>(.+?)</h1>", re.I | re.S),
            "fail": "缺少 <h1> 主标题，读者无法在 3 秒内识别主题",
        },
        "has_body_content": {
            "check": re.compile(r"<(?:p|section|article|div)[^>]*>.+?</(?:p|section|article|div)>", re.I | re.S),
            "fail": "正文区域无内容",
        },
        "no_empty_sections": {
            "check": re.compile(r"<section[^>]*>\s*</section>", re.I),
            "fail": "存在空的 <section>，可能是占位符未填充",
            "invert": True,  # 不应该匹配
        },
    }

    # ============================================================
    # Gate 2: 视觉密度基准
    # ============================================================
    # 封面类产出的最低视觉密度要求
    COVER_MIN_REQUIREMENTS = {
        "min_font_levels": 3,  # 至少 3 级字号
        "min_anchor_points": 3,  # 至少 3 个视觉锚点
        "min_color_count": 2,  # 至少 2 种颜色
    }
    # 文章类产出的最低视觉密度要求
    ARTICLE_MIN_REQUIREMENTS = {
        "min_font_levels": 2,
        "min_anchor_points": 2,
        "min_color_count": 2,
    }

    # ============================================================
    # Gate 3: 可编辑交付
    # ============================================================
    GATE3_RULES = {
        "no_hardcoded_images": {
            "check": re.compile(r'src="(?:data:image|file://)', re.I),
            "fail": "发现 base64 或本地文件协议图片，不利于编辑和协作",
            "invert": True,
        },
        "has_meta_charset": {
            "check": re.compile(r"<meta[^>]+charset", re.I),
            "fail": "缺少 <meta charset>，可能导致编码问题",
        },
        "no_inline_js": {
            "check": re.compile(r"<script", re.I),
            "fail": "内嵌 <script>，公众号不支持",
            "invert": True,
        },
    }

    # ---------- 公开接口 ----------
    def audit_html_cover(self, html_path: Path) -> AuditReport:
        """审计封面类 HTML（21:9 封面、社交卡片）"""
        text = html_path.read_text(encoding="utf-8")
        report = AuditReport(target=str(html_path))
        report.gates.append(self._gate1(text, kind="cover"))
        report.gates.append(self._gate2(text, kind="cover"))
        report.gates.append(self._gate3(text))
        return report

    def audit_html_article(self, html_path: Path) -> AuditReport:
        """审计文章类 HTML（公众号正文）"""
        text = html_path.read_text(encoding="utf-8")
        report = AuditReport(target=str(html_path))
        report.gates.append(self._gate1(text, kind="article"))
        report.gates.append(self._gate2(text, kind="article"))
        report.gates.append(self._gate3(text))
        return report

    # ---------- Gate 1 ----------
    def _gate1(self, html: str, kind: str = "article") -> GateResult:
        """主题与载体合理性"""
        result = GateResult(gate="Gate 1", name="主题与载体合理性", status=GateStatus.PASS)
        for rule_id, rule in self.GATE1_RULES.items():
            result.checks_total += 1
            matched = bool(rule["check"].search(html))
            is_invert = rule.get("invert", False)
            if is_invert:
                passed = not matched
            else:
                passed = matched
            if passed:
                result.checks_passed += 1
            else:
                result.issues.append(rule["fail"])
        result.status = GateStatus.PASS if not result.issues else GateStatus.FAIL
        result.notes.append(f"载体类型: {kind}")
        return result

    # ---------- Gate 2 ----------
    def _gate2(self, html: str, kind: str = "article") -> GateResult:
        """视觉密度基准对照"""
        reqs = self.COVER_MIN_REQUIREMENTS if kind == "cover" else self.ARTICLE_MIN_REQUIREMENTS
        result = GateResult(gate="Gate 2", name="视觉密度基准", status=GateStatus.PASS)

        # 字号层级数
        font_sizes = set(re.findall(r"font-size:\s*(\d+)px", html, re.I))
        result.checks_total += 1
        if len(font_sizes) >= reqs["min_font_levels"]:
            result.checks_passed += 1
            result.notes.append(f"字号层级: {len(font_sizes)} 级 ({', '.join(sorted(font_sizes))}px)")
        else:
            result.issues.append(f"字号层级不足: 仅 {len(font_sizes)} 级，要求 ≥{reqs['min_font_levels']}")

        # 视觉锚点（标题数 + 引用块数 + 强调色出现次数）
        headings = len(re.findall(r"<h[1-4][^>]*>", html, re.I))
        quotes = len(re.findall(r"border-left:", html, re.I))
        anchors = headings + quotes
        result.checks_total += 1
        if anchors >= reqs["min_anchor_points"]:
            result.checks_passed += 1
            result.notes.append(f"视觉锚点: {anchors} 个（标题{headings}+引用{quotes}）")
        else:
            result.issues.append(f"视觉锚点不足: {anchors} 个，要求 ≥{reqs['min_anchor_points']}")

        # 颜色丰富度
        colors = set(re.findall(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b", html))
        result.checks_total += 1
        if len(colors) >= reqs["min_color_count"]:
            result.checks_passed += 1
            result.notes.append(f"颜色数: {len(colors)} 种")
        else:
            result.issues.append(f"颜色过于单一: 仅 {len(colors)} 种，要求 ≥{reqs['min_color_count']}")

        result.status = GateStatus.PASS if not result.issues else GateStatus.WARN
        return result

    # ---------- Gate 3 ----------
    def _gate3(self, html: str) -> GateResult:
        """可编辑交付"""
        result = GateResult(gate="Gate 3", name="可编辑交付", status=GateStatus.PASS)
        for rule_id, rule in self.GATE3_RULES.items():
            result.checks_total += 1
            matched = bool(rule["check"].search(html))
            is_invert = rule.get("invert", False)
            passed = not matched if is_invert else matched
            if passed:
                result.checks_passed += 1
            else:
                result.issues.append(rule["fail"])
        result.status = GateStatus.PASS if not result.issues else GateStatus.FAIL
        return result
