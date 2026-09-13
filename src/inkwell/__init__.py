"""inkwell: Markdown → 公众号 HTML 发布流水线

把 Markdown 转成公众号兼容 HTML，
支持图片压缩 + 双版本（CDN 外链 / base64 本地预览）输出。
内置内容搜索、草稿生成、封面设计、社交卡片、设计审计、
敏感词检测、目录生成、字数统计全链路。
"""

from .core import Pipeline, PipelineConfig, PipelineResult
from .cover_advisor import CoverAdvice, CoverAdvisor
from .cover_gen import CoverGenerator, CoverSpec
from .design_audit import AuditReport, DesignAuditor, GateResult, GateStatus
from .generator import DraftGenerator
from .processors.image_proc import ImageProcessor
from .processors.markdown_proc import THEME_META, THEMES, MarkdownProcessor
from .processors.validator import CopyCompatValidator
from .publisher import Publisher, PublishResult
from .screenshot import Screenshotter
from .searcher import ContentSearcher, SearchResult
from .social_card import PLATFORM_SPECS, STYLE_PRESETS, CardPage, CardSpec, SocialCardGenerator
from .stats import ArticleAnalyzer, ArticleStats
from .toc import Heading, TOCGenerator, TOCResult
from .wordcheck import WordChecker, WordCheckReport, WordHit

__version__ = "0.7.8"

__all__ = [
    # 流水线核心
    "Pipeline",
    "PipelineConfig",
    "PipelineResult",
    # 排版
    "MarkdownProcessor",
    "THEMES",
    "THEME_META",
    # 图片
    "ImageProcessor",
    # 校验
    "CopyCompatValidator",
    # 搜索
    "ContentSearcher",
    "SearchResult",
    # 草稿生成
    "DraftGenerator",
    # 设计审计
    "DesignAuditor",
    "AuditReport",
    "GateResult",
    "GateStatus",
    # 封面生成
    "CoverGenerator",
    "CoverSpec",
    # 社交卡片
    "SocialCardGenerator",
    "CardSpec",
    "CardPage",
    "PLATFORM_SPECS",
    "STYLE_PRESETS",
    # 封面顾问
    "CoverAdvisor",
    "CoverAdvice",
    # 截图
    "Screenshotter",
    # 发布
    "Publisher",
    "PublishResult",
    # 敏感词检测
    "WordChecker",
    "WordCheckReport",
    "WordHit",
    # 目录生成
    "TOCGenerator",
    "TOCResult",
    "Heading",
    # 字数统计
    "ArticleAnalyzer",
    "ArticleStats",
    "__version__",
]
