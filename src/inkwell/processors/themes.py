"""排版主题色板（从 markdown_proc.py 抽出）

15 套主题，每套有独立色板和字体栈，共用同一套转换逻辑。
需要新增主题时只改这个文件，不碰转换代码。
"""

from __future__ import annotations

# ============================================================
# 主题色板
# ============================================================
THEMES: dict[str, dict[str, str]] = {
    # --- 摸鱼绿 ---
    "moyu-green": {
        "bg": "#FFFFFF",
        "text": "#1F2937",
        "primary": "#059669",
        "accent": "#A7F3D0",
        "highlight": "#065F46",
        "underline": "#A7F3D0",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 红白色系 ---
    "red-white": {
        "bg": "#FFFFFF",
        "text": "#1F2937",
        "primary": "#DC2626",
        "accent": "#FECACA",
        "highlight": "#991B1B",
        "underline": "#FECACA",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 石墨极简风 ---
    "graphite-minimal": {
        "bg": "#FAFAFA",
        "text": "#3F3F46",
        "primary": "#52525B",
        "accent": "#A1A1AA",
        "highlight": "#27272A",
        "underline": "#52525B",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 留白禅意风 ---
    "zen-whitespace": {
        "bg": "#FDFCFB",
        "text": "#3D4F44",
        "primary": "#4A5D52",
        "accent": "#B5C8BC",
        "highlight": "#2D3B33",
        "underline": "#B5C8BC",
        "font": "'Songti SC', 'Noto Serif SC', serif",
    },
    # --- 摸鱼票据风 ---
    "moyu-ticket": {
        "bg": "#FFFBEB",
        "text": "#1F2937",
        "primary": "#059669",
        "accent": "#FCD34D",
        "highlight": "#92400E",
        "underline": "#A7F3D0",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 橄榄手记 ---
    "olive-journal": {
        "bg": "#F5F5F0",
        "text": "#2C2C2A",
        "primary": "#1E1F23",
        "accent": "#ED7B2F",
        "highlight": "#1E1F23",
        "underline": "#ED7B2F",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 经典衬线（原 editorial-oldmoney） ---
    "classic-serif": {
        "bg": "#FAF8F5",
        "text": "#2C2C2A",
        "primary": "#1B3A2E",
        "accent": "#C8A35E",
        "highlight": "#5C1A1B",
        "underline": "#C8A35E",
        "font": "Georgia, 'Songti SC', 'Noto Serif SC', serif",
    },
    # --- 赛博朋克霓虹（暗色科技风） ---
    "cyber-neon": {
        "bg": "#0D0D1A",
        "text": "#C8C8E0",
        "primary": "#00F0FF",
        "accent": "#FF00AA",
        "highlight": "#FFD700",
        "underline": "#00F0FF",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 咖啡摩卡（暖调生活风） ---
    "coffee-mocha": {
        "bg": "#F5EDE0",
        "text": "#3E2C1C",
        "primary": "#6F4E37",
        "accent": "#C9A87C",
        "highlight": "#8B5A2B",
        "underline": "#C9A87C",
        "font": "Georgia, 'Songti SC', serif",
    },
    # --- 海洋蓝（商务财经风） ---
    "ocean-blue": {
        "bg": "#FFFFFF",
        "text": "#1A2B3C",
        "primary": "#0066CC",
        "accent": "#4FC3F7",
        "highlight": "#0D47A1",
        "underline": "#4FC3F7",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 日落暖橙（生活方式风） ---
    "sunset-warm": {
        "bg": "#FFF8F0",
        "text": "#4A2C20",
        "primary": "#E76F51",
        "accent": "#F4A261",
        "highlight": "#A8472A",
        "underline": "#F4A261",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 水墨山水（传统文化风） ---
    "ink-wash": {
        "bg": "#F8F6F1",
        "text": "#2B2B2B",
        "primary": "#1A1A1A",
        "accent": "#888888",
        "highlight": "#555555",
        "underline": "#AAAAAA",
        "font": "'Songti SC', 'Noto Serif SC', serif",
    },
    # --- 森林深绿（自然环保风） ---
    "forest-deep": {
        "bg": "#F4F7F5",
        "text": "#1C3329",
        "primary": "#2D6A4F",
        "accent": "#95D5B2",
        "highlight": "#1B4332",
        "underline": "#95D5B2",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 皇家紫（创意设计风） ---
    "royal-purple": {
        "bg": "#FAF7FF",
        "text": "#2D1B4E",
        "primary": "#6A1B9A",
        "accent": "#CE93D8",
        "highlight": "#4A148C",
        "underline": "#CE93D8",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
    # --- 樱花粉（时尚美妆风） ---
    "sakura-pink": {
        "bg": "#FFF5F7",
        "text": "#3D2020",
        "primary": "#E91E63",
        "accent": "#F8BBD0",
        "highlight": "#AD1457",
        "underline": "#F8BBD0",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
    },
}

# 向后兼容别名
THEMES["editorial-oldmoney"] = THEMES["classic-serif"]

# 主题元信息（用于 CLI 列表展示）
THEME_META: list[dict[str, str]] = [
    {"id": "moyu-green", "name": "摸鱼绿", "desc": "教程、测评、清单、工具盘点"},
    {"id": "red-white", "name": "红白色系", "desc": "深度分析、观点、力量感话题"},
    {"id": "graphite-minimal", "name": "石墨极简", "desc": "设计、科技评论、专业观点"},
    {"id": "zen-whitespace", "name": "留白禅意", "desc": "禅意、极简生活、深度随笔"},
    {"id": "moyu-ticket", "name": "摸鱼票据", "desc": "测评、工具对比（票据视觉）"},
    {"id": "olive-journal", "name": "橄榄手记", "desc": "内刊手记、深度评测、案例复盘"},
    {"id": "classic-serif", "name": "经典衬线", "desc": "深度长文、编辑部风格"},
    {"id": "cyber-neon", "name": "赛博霓虹", "desc": "科技、AI、编程、暗色酷炫"},
    {"id": "coffee-mocha", "name": "咖啡摩卡", "desc": "生活、美食、旅行、暖调随笔"},
    {"id": "ocean-blue", "name": "海洋蓝", "desc": "商务、财经、行业分析、职场"},
    {"id": "sunset-warm", "name": "日落暖橙", "desc": "生活方式、品牌故事、情感"},
    {"id": "ink-wash", "name": "水墨山水", "desc": "传统文化、诗词、人文历史"},
    {"id": "forest-deep", "name": "森林深绿", "desc": "环保、自然、可持续发展、健康"},
    {"id": "royal-purple", "name": "皇家紫", "desc": "创意、设计、艺术、灵感"},
    {"id": "sakura-pink", "name": "樱花粉", "desc": "时尚、美妆、穿搭、少女心"},
]
