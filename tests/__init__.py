"""pytest 配置"""

import sys
from pathlib import Path

# 把 src 加入 path，方便直接 pytest 跑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
