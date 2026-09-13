"""公众号剪贴板兼容性静态扫描

用户记忆中的铁律校验：
- 严禁 display:flex / grid
- 严禁 inline-block 自制图形（圆点、方块）
- 严禁 linear-gradient 渐变
- 严禁 SVG / CSS 三角形装饰箭头
- 严禁 data:image base64 内嵌图（发布版）
- 正文文字节点必须包在 <span leaf=""> 内（否则粘贴后样式大面积丢失）

⚠️ 扫描前必须剥掉**文本节点**：文章正文里出现「linear-gradient」这类词
（比如这篇稿子正好在讲解这个坑）会被 FORBIDDEN 正则当成 CSS 命中。
CSS 只可能出现在标签名与属性值里，所以先删掉 `>...<` 之间的文字再扫。
"""

from __future__ import annotations

import re
from pathlib import Path


class CopyCompatValidator:
    FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern]] = [
        ("display:flex/grid", re.compile(r"display:\s*(?:flex|grid)", re.I)),
        ("inline-block 自制图形", re.compile(r"display:\s*inline-block", re.I)),
        ("linear-gradient 渐变", re.compile(r"linear-gradient", re.I)),
        ("SVG 装饰", re.compile(r"<svg", re.I)),
        ("base64 内嵌图", re.compile(r"data:image/[^;]+;base64", re.I)),
    ]

    # 文本节点：位于 > 与 < 之间（不含尖括号）的内容
    TEXT_NODE_RE = re.compile(r">[^<>]*<")
    CJK_RE = re.compile(r"[\u4e00-\u9fff]")
    LEAF_RE = re.compile(r"<span\b[^>]*\bleaf\b", re.I)

    @staticmethod
    def markup_only(html: str) -> str:
        """只保留标签与属性，剥掉全部文本节点"""
        return CopyCompatValidator.TEXT_NODE_RE.sub("><", html)

    def scan(self, html_path: Path) -> list[str]:
        """返回警告列表，空列表表示完全兼容"""
        text = html_path.read_text(encoding="utf-8")
        markup = self.markup_only(text)

        warnings: list[str] = []
        for name, pat in self.FORBIDDEN_PATTERNS:
            matches = pat.findall(markup)
            if matches:
                warnings.append(f"⚠️ 发现 {len(matches)} 处 {name}")

        # leaf 检查：无中文的纯英文片段不适用（也不该报）
        if self.CJK_RE.search(text) and not self.LEAF_RE.search(markup):
            warnings.append('⚠️ 正文没有任何 <span leaf=""> 包裹，粘贴到公众号后样式会大面积丢失')

        if not warnings:
            print("[validator] 公众号兼容性校验通过 ✓")
        else:
            print(f"[validator] 发现 {len(warnings)} 类兼容性风险")
        return warnings
