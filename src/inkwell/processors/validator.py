"""公众号剪贴板兼容性静态扫描

用户记忆中的铁律校验：
- 严禁 display:flex / grid
- 严禁 inline-block 自制图形（圆点、方块）
- 严禁 linear-gradient 渐变
- 严禁 SVG / CSS 三角形装饰箭头
- 严禁 data:image base64 内嵌图（发布版）
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

    def scan(self, html_path: Path) -> list[str]:
        """返回警告列表，空列表表示完全兼容"""
        text = html_path.read_text(encoding="utf-8")
        # 只扫描 #article 正文区域（用户记忆里的 copy 脚本只 clone #article）
        # 这里简化为全文扫描
        warnings: list[str] = []
        for name, pat in self.FORBIDDEN_PATTERNS:
            matches = pat.findall(text)
            if matches:
                warnings.append(f"⚠️ 发现 {len(matches)} 处 {name}")
        if not warnings:
            print("[validator] 公众号兼容性校验通过 ✓")
        else:
            print(f"[validator] 发现 {len(warnings)} 类兼容性风险")
        return warnings
