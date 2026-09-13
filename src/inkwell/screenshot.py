"""Playwright 截图封装（Python → Node.js 调用）

把 HTML 封面/卡片截图为 PNG，支持精确尺寸和 Retina 高清输出。

用法：
    shooter = Screenshotter()
    shooter.capture(Path("cover.html"), Path("cover.png"), width=2100, height=900)
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# 缺少 Playwright 时的统一安装指引
INSTALL_HINT = (
    "PNG 截图需要 Playwright。安装方式：\n"
    "  npm install -g playwright-core\n"
    "  npx playwright install chromium\n"
    "或指定已有环境：export PLAYWRIGHT_NODE_PATH=/path/to/node_modules\n"
    "（HTML 文件已正常生成，仅 PNG 输出被跳过）"
)


class ScreenshotError(RuntimeError):
    """截图失败（含依赖缺失、浏览器缺失等情况）"""


class Screenshotter:
    """调用 Node.js Playwright 截图

    依赖：playwright-core + Chromium（自动检测路径）
    """

    # 封面/卡片的标准尺寸
    SIZES: dict[str, tuple[int, int]] = {
        "21x9": (2100, 900),
        "1x1": (1080, 1080),
        "3x4": (1080, 1440),
        "16x9": (1920, 1080),
        "4:3": (1440, 1080),
    }

    def __init__(self) -> None:
        self._node = self._find_node()
        self._script = Path(__file__).parent / "screenshot.js"
        self._node_path = self._find_node_path()

    @classmethod
    def is_available(cls) -> bool:
        """Playwright 截图链路是否可用（Node + playwright-core 齐备）"""
        if not cls._find_node():
            return False
        return cls._find_node_path() is not None

    def check_ready(self) -> None:
        """提前校验截图链路，缺失时抛出带安装指引的异常"""
        if not self._node:
            raise ScreenshotError(
                "未找到 Node.js，无法执行 PNG 截图。\n请安装 Node.js 18+ 并确保在 PATH 中。\n" + INSTALL_HINT
            )
        if not self._node_path:
            raise ScreenshotError("未找到 playwright-core。\n" + INSTALL_HINT)

    def capture(
        self,
        html_path: Path,
        output_png: Path,
        width: int = 1080,
        height: int = 1080,
    ) -> Path:
        """截图 HTML → PNG

        Args:
            html_path:  HTML 文件路径
            output_png: 输出 PNG 路径
            width:      视口宽度
            height:     视口高度

        Returns: output_png 路径

        Raises: ScreenshotError（依赖缺失或渲染失败，消息含修复指引）
        """
        self.check_ready()
        output_png.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self._node,
            str(self._script),
            str(html_path),
            str(output_png),
            str(width),
            str(height),
        ]

        env = {**os.environ}
        if self._node_path:
            env["NODE_PATH"] = self._node_path

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
        except subprocess.TimeoutExpired as exc:
            raise ScreenshotError("截图超时（60s），HTML 可能含阻塞资源。") from exc

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            # 浏览器可执行文件缺失时给出可执行的修复提示
            if "Executable doesn't exist" in detail:
                raise ScreenshotError(
                    "Chromium 浏览器未安装或版本不匹配。\n"
                    "执行：npx playwright install chromium\n"
                    f"原始错误：{detail.splitlines()[0]}"
                )
            raise ScreenshotError(f"截图失败：{detail[:500]}")
        return output_png

    def capture_by_format(self, html_path: Path, output_png: Path, fmt: str) -> Path:
        """按格式名截图（21x9 / 1x1 / 3x4 / 16:9）"""
        fmt_key = fmt.replace(" ", "").lower()
        if fmt_key not in self.SIZES:
            raise ValueError(f"未知格式: {fmt}，可选: {list(self.SIZES)}")
        w, h = self.SIZES[fmt_key]
        return self.capture(html_path, output_png, w, h)

    @staticmethod
    def _find_node() -> str | None:
        """查找可用的 Node.js"""
        return shutil.which("node")

    @staticmethod
    def _find_node_path() -> str | None:
        """查找 playwright-core 所在的 node_modules 路径

        按优先级依次检测：
        1. 环境变量 PLAYWRIGHT_NODE_PATH
        2. 全局 npm root
        3. 当前目录的 node_modules
        """
        # 1. 环境变量显式指定
        env_path = os.environ.get("PLAYWRIGHT_NODE_PATH")
        if env_path and Path(env_path).exists():
            return env_path

        # 2. 全局 npm root
        npm = shutil.which("npm")
        if npm:
            try:
                result = subprocess.run(
                    [npm, "root", "-g"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    global_nm = result.stdout.strip()
                    if (Path(global_nm) / "playwright-core").exists():
                        return global_nm
            except Exception:
                pass

        # 3. 本地 node_modules
        local_nm = Path.cwd() / "node_modules"
        if (local_nm / "playwright-core").exists():
            return str(local_nm)

        return None
