"""社交卡片生成器

平台规格和布局配方：
  中文平台：
    - 小红书 3:4 竖图轮播（封面 + 内容页）
    - 公众号 21:9 + 1:1 封面对
    - 公众号正文图 16:9
    - 微博 1:1
  海外平台：
    - Instagram Feed 1:1 轮播
    - Instagram Story / TikTok 9:16 竖屏
    - X (Twitter) 16:9
    - LinkedIn 1.91:1
    - Pinterest 2:3
    - YouTube Thumbnail 16:9
  通用社交卡片：Swiss 极简风、Editorial 杂志风

输出独立 HTML 文件，可在浏览器查看或截图为 PNG。
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================
# 平台规格
# ============================================================
PLATFORM_SPECS: dict[str, dict] = {
    # ====================================================
    # 中文平台
    # ====================================================
    "xhs": {  # 小红书
        "name": "小红书",
        "ratio": "3:4",
        "width": 1080,
        "height": 1440,
        "max_pages": 9,
        "safe_margin": 60,
        "region": "cn",
    },
    "wechat-cover": {  # 公众号封面
        "name": "公众号封面",
        "ratio": "21:9 + 1:1",
        "width": 2100,
        "height": 900,
        "square_width": 1080,
        "square_height": 1080,
        "safe_margin": 80,
        "region": "cn",
    },
    "wechat-article": {  # 公众号正文图
        "name": "公众号正文图",
        "ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "safe_margin": 40,
        "region": "cn",
    },
    "weibo": {  # 微博
        "name": "微博",
        "ratio": "1:1 或 16:9",
        "width": 1080,
        "height": 1080,
        "safe_margin": 40,
        "region": "cn",
    },
    # ====================================================
    # 海外平台
    # ====================================================
    "instagram-feed": {  # Instagram Feed 轮播
        "name": "Instagram Feed",
        "ratio": "1:1",
        "width": 1080,
        "height": 1080,
        "max_pages": 10,
        "safe_margin": 50,
        "region": "global",
    },
    "instagram-story": {  # Instagram Story / Reels
        "name": "Instagram Story / Reels",
        "ratio": "9:16",
        "width": 1080,
        "height": 1920,
        "safe_margin": 80,
        "region": "global",
    },
    "x-twitter": {  # X (Twitter)
        "name": "X (Twitter)",
        "ratio": "16:9",
        "width": 1600,
        "height": 900,
        "safe_margin": 40,
        "region": "global",
    },
    "linkedin": {  # LinkedIn
        "name": "LinkedIn",
        "ratio": "1.91:1",
        "width": 1200,
        "height": 627,
        "safe_margin": 40,
        "region": "global",
    },
    "pinterest": {  # Pinterest
        "name": "Pinterest",
        "ratio": "2:3",
        "width": 1000,
        "height": 1500,
        "safe_margin": 50,
        "region": "global",
    },
    "youtube-thumb": {  # YouTube Thumbnail
        "name": "YouTube Thumbnail",
        "ratio": "16:9",
        "width": 1280,
        "height": 720,
        "safe_margin": 30,
        "region": "global",
    },
    # ====================================================
    # 通用
    # ====================================================
    "generic": {
        "name": "通用",
        "ratio": "1:1",
        "width": 1080,
        "height": 1080,
        "safe_margin": 40,
        "region": "global",
    },
}

# ============================================================
# 视觉风格预设
# ============================================================
STYLE_PRESETS: dict[str, dict[str, str]] = {
    "swiss": {  # Swiss 极简
        "bg": "#F5F5F0",
        "text": "#1A1A1A",
        "primary": "#D62828",
        "accent": "#003049",
        "font": "'Inter', 'PingFang SC', sans-serif",
        "grid": "visible",
    },
    "editorial": {  # Editorial 杂志风
        "bg": "#0E0D0C",
        "text": "#ECE2CF",
        "primary": "#D4A04A",
        "accent": "#ECE2CF",
        "font": "'Noto Serif SC', Georgia, serif",
        "grid": "hidden",
    },
    "clean-light": {  # 干净浅色
        "bg": "#FFFFFF",
        "text": "#333333",
        "primary": "#0066CC",
        "accent": "#FF6600",
        "font": "'PingFang SC', 'Helvetica Neue', sans-serif",
        "grid": "hidden",
    },
    "dark-bold": {  # 深色大胆
        "bg": "#1A1A2E",
        "text": "#EAEAEA",
        "primary": "#E94560",
        "accent": "#0F3460",
        "font": "'Inter', 'PingFang SC', sans-serif",
        "grid": "hidden",
    },
}


@dataclass
class CardPage:
    """单张卡片内容"""

    title: str = ""
    subtitle: str = ""
    body: str = ""  # 要点文本（支持换行）
    image_placeholder: str = ""  # 图片占位说明
    page_num: int = 1
    total_pages: int = 1


@dataclass
class CardSpec:
    """社交卡片完整规格"""

    platform: str = "xhs"  # xhs / instagram-feed / instagram-story / x-twitter / linkedin / pinterest / youtube-thumb / wechat-cover / wechat-article / weibo / generic
    style: str = "swiss"  # swiss / editorial / clean-light / dark-bold
    pages: list[CardPage] = field(default_factory=list)
    brand: str = ""  # 品牌/作者署名
    tag: str = ""  # 标签（如 #AI工具 #测评）


# ============================================================
# 卡片 HTML 模板（通用参数化，适配所有比例）
# ============================================================

CARD_COVER_TEMPLATE = textwrap.dedent("""\
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_title}</title>
</head>
<body style="margin:0;padding:0;background-color:{bg};">
<section data-vds-schema="v3.1" data-vds-role="social-card" data-vds-format="{vds_format}"
  style="width:100%;max-width:{width}px;aspect-ratio:{ratio_w}/{ratio_h};margin:0 auto;
         background-color:{bg};color:{text};position:relative;overflow:hidden;
         font-family:{font};padding:0;box-sizing:border-box;">

  <!-- 背景水印期号（填充留白，增加层次） -->
  <span style="position:absolute;right:-16px;bottom:-56px;z-index:0;
        font-size:{watermark_size}px;font-style:italic;font-weight:bold;
        line-height:0.8;letter-spacing:-10px;
        color:{primary};opacity:0.06;">{watermark_num}</span>

  <!-- 三段式布局：顶部标识 / 中部主体（垂直居中）/ 底部署名 -->
  <table style="width:100%;height:100%;border-collapse:collapse;table-layout:fixed;
                position:relative;z-index:1;">

    <!-- 顶部区域 -->
    <tr>
      <td style="border:none;padding:{pad_v}px {pad_h}px 0;vertical-align:top;">
        <table style="width:100%;border-collapse:collapse;border:none;"><tr>
          <td style="border:none;padding:0;">
            <span style="font-size:{tag_size}px;letter-spacing:3px;text-transform:uppercase;
                  color:{primary};font-weight:bold;">{tag}</span>
          </td>
          <td style="border:none;padding:0;text-align:right;">
            <span style="font-size:13px;color:{text};opacity:0.4;letter-spacing:2px;">{brand}</span>
          </td>
        </tr></table>
        <div style="margin-top:16px;height:2px;background-color:{primary};opacity:0.8;width:48px;"></div>
      </td>
    </tr>

    <!-- 中部主体（垂直居中，撑满剩余空间） -->
    <tr>
      <td style="border:none;padding:0 {pad_h}px;vertical-align:middle;height:100%;">
        <h1 style="font-size:{title_size}px;font-weight:bold;line-height:1.25;margin:0;
              color:{text};letter-spacing:-1px;">{heading_text}</h1>
        <p style="font-size:{sub_size}px;line-height:1.5;margin:20px 0 0;
           color:{text};opacity:0.6;font-style:italic;">{subtitle}</p>
        <div style="margin:32px 0;height:1px;background-color:{primary};opacity:0.2;"></div>
        <p style="font-size:{body_size}px;line-height:1.9;margin:0;
           color:{text};opacity:0.85;white-space:pre-line;">{body}</p>
      </td>
    </tr>

    <!-- 底部装饰 -->
    <tr>
      <td style="border:none;padding:0 {pad_h}px {pad_v}px;vertical-align:bottom;">
        <div style="height:1px;background-color:{primary};opacity:0.3;margin-bottom:16px;"></div>
        <table style="width:100%;border-collapse:collapse;border:none;"><tr>
          <td style="border:none;padding:0;">
            <span style="font-size:13px;color:{primary};letter-spacing:2px;font-weight:bold;">{brand}</span>
          </td>
          <td style="border:none;padding:0;text-align:right;">
            <span style="font-size:13px;color:{text};opacity:0.4;letter-spacing:1px;">01 / {total_str}</span>
          </td>
        </tr></table>
      </td>
    </tr>

  </table>
</section>
</body>
</html>
""")

CARD_CONTENT_TEMPLATE = textwrap.dedent("""\
<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_title} - {page_label}</title>
</head>
<body style="margin:0;padding:0;background-color:{bg};">
<section data-vds-schema="v3.1" data-vds-role="social-card" data-vds-format="{vds_format}"
  style="width:100%;max-width:{width}px;aspect-ratio:{ratio_w}/{ratio_h};margin:0 auto;
         background-color:{bg};color:{text};position:relative;overflow:hidden;
         font-family:{font};padding:0;box-sizing:border-box;">

  <!-- 背景水印页码（填充留白，增加层次） -->
  <span style="position:absolute;right:-16px;bottom:-56px;z-index:0;
        font-size:{watermark_size}px;font-style:italic;font-weight:bold;
        line-height:0.8;letter-spacing:-10px;
        color:{primary};opacity:0.05;">{watermark_num}</span>

  <!-- 三段式布局：顶部页码 / 中部主体（垂直居中）/ 底部署名 -->
  <table style="width:100%;height:100%;border-collapse:collapse;table-layout:fixed;
                position:relative;z-index:1;">

    <!-- 顶部区域 -->
    <tr>
      <td style="border:none;padding:{pad_v}px {pad_h}px 0;vertical-align:top;">
        <table style="width:100%;border-collapse:collapse;border:none;"><tr>
          <td style="border:none;padding:0;">
            <span style="font-size:14px;letter-spacing:3px;color:{primary};opacity:0.7;
                  font-weight:bold;">{page_zero}</span>
          </td>
          <td style="border:none;padding:0;text-align:right;">
            <span style="font-size:13px;color:{text};opacity:0.4;letter-spacing:2px;">{brand}</span>
          </td>
        </tr></table>
        <div style="margin-top:12px;height:2px;background-color:{primary};opacity:0.5;width:36px;"></div>
      </td>
    </tr>

    <!-- 中部主体（垂直居中，撑满剩余空间） -->
    <tr>
      <td style="border:none;padding:0 {pad_h}px;vertical-align:middle;height:100%;">
        <h2 style="font-size:{heading_size}px;font-weight:bold;line-height:1.25;margin:0;
              color:{text};">{heading_text}</h2>
        <p style="font-size:{sub_size}px;line-height:1.5;margin:16px 0 0;
           color:{text};opacity:0.55;font-style:italic;">{subtitle}</p>
        <div style="margin:32px 0;height:1px;background-color:{primary};opacity:0.2;"></div>
        <p style="font-size:{body_size}px;line-height:1.9;margin:0;
           color:{text};opacity:0.85;white-space:pre-line;">{body}</p>
      </td>
    </tr>

    <!-- 底部装饰 -->
    <tr>
      <td style="border:none;padding:0 {pad_h}px {pad_v}px;vertical-align:bottom;">
        <div style="height:1px;background-color:{primary};opacity:0.25;margin-bottom:14px;"></div>
        <table style="width:100%;border-collapse:collapse;border:none;"><tr>
          <td style="border:none;padding:0;">
            <span style="font-size:13px;color:{primary};letter-spacing:2px;font-weight:bold;">{brand}</span>
          </td>
          <td style="border:none;padding:0;text-align:right;">
            <span style="font-size:13px;color:{text};opacity:0.4;letter-spacing:1px;">{page_str} / {total_str}</span>
          </td>
        </tr></table>
      </td>
    </tr>

  </table>
</section>
</body>
</html>
""")


class SocialCardGenerator:
    """社交卡片生成器

    用法：
        gen = SocialCardGenerator()
        spec = CardSpec(
            platform="xhs",
            style="swiss",
            pages=[CardPage(title="...", body="...")],
        )
        paths = gen.generate(spec, output_dir=Path("./cards"))
    """

    def generate(self, spec: CardSpec, output_dir: Path, png: bool = False) -> list[Path]:
        """生成完整卡片组，返回文件路径列表（HTML 或 PNG）"""
        output_dir.mkdir(parents=True, exist_ok=True)

        if spec.platform not in PLATFORM_SPECS:
            raise ValueError(f"不支持的平台: {spec.platform}")
        if spec.style not in STYLE_PRESETS:
            raise ValueError(f"不支持的风格: {spec.style}")

        plat = PLATFORM_SPECS[spec.platform]
        preset = STYLE_PRESETS[spec.style]
        total = len(spec.pages)

        # 比例参数
        w = plat["width"]
        h = plat.get("height", w)
        ratio_w, ratio_h = self._parse_ratio(plat["ratio"], w, h)
        vds_format = f"{ratio_w}x{ratio_h}" if ratio_w != ratio_h else "1x1"

        # 安全边距（按比例缩放）
        safe = plat.get("safe_margin", 40)
        pad_h = safe
        pad_v = safe

        # 自适应字号（基于高度等比缩放，以 1440 为基准）
        scale = h / 1440 if h > w else w / 1080
        scale = max(0.5, min(1.2, scale))
        tag_size = round(16 * scale)
        title_size = round(78 * scale)
        sub_size = round(24 * scale)
        body_size = round(max(16, 20 * scale))
        heading_size = round(54 * scale)
        watermark_size = round(max(h, w) * 0.55)

        # 语言
        lang = (
            "en"
            if plat.get("region") == "global" and spec.platform not in ("wechat-cover", "wechat-article")
            else "zh-CN"
        )

        html_paths: list[Path] = []

        for i, page in enumerate(spec.pages):
            page.page_num = i + 1
            page.total_pages = total

            if i == 0:
                html = CARD_COVER_TEMPLATE.format(
                    lang=lang,
                    html_title=page.title,
                    bg=preset["bg"],
                    text=preset["text"],
                    primary=preset["primary"],
                    font=preset["font"],
                    width=w,
                    ratio_w=ratio_w,
                    ratio_h=ratio_h,
                    vds_format=vds_format,
                    pad_v=pad_v,
                    pad_h=pad_h,
                    tag_size=tag_size,
                    title_size=title_size,
                    sub_size=sub_size,
                    body_size=body_size,
                    heading_size=heading_size,
                    tag=spec.tag or ("Content Series" if lang == "en" else "内容系列"),
                    heading_text=page.title,
                    subtitle=page.subtitle,
                    body=page.body,
                    brand=spec.brand,
                    total_str=f"{total:02d}",
                    watermark_num="01",
                    watermark_size=watermark_size,
                )
                fname = f"card_cover_{spec.platform}.html"
            else:
                title_text = page.title or f"第{page.page_num}页"
                html = CARD_CONTENT_TEMPLATE.format(
                    lang=lang,
                    html_title=title_text,
                    bg=preset["bg"],
                    text=preset["text"],
                    primary=preset["primary"],
                    font=preset["font"],
                    width=w,
                    ratio_w=ratio_w,
                    ratio_h=ratio_h,
                    vds_format=vds_format,
                    pad_v=pad_v,
                    pad_h=pad_h,
                    heading_size=heading_size,
                    body_size=body_size,
                    sub_size=sub_size,
                    page_label=f"{page.page_num:02d}",
                    page_zero=f"{page.page_num:02d}",
                    heading_text=title_text,
                    subtitle=page.subtitle,
                    body=page.body,
                    brand=spec.brand,
                    page_str=f"{page.page_num:02d}",
                    total_str=f"{total:02d}",
                    watermark_num=f"{page.page_num:02d}",
                    watermark_size=watermark_size,
                )
                fname = f"card_p{page.page_num}_{spec.platform}.html"

            fpath = output_dir / fname
            fpath.write_text(html, encoding="utf-8")
            html_paths.append(fpath)

        if png:
            from .screenshot import ScreenshotError, Screenshotter

            try:
                shooter = Screenshotter()
                png_paths: list[Path] = []
                for hp in html_paths:
                    pp = hp.with_suffix(".png")
                    shooter.capture(hp, pp, w, h)
                    png_paths.append(pp)
            except ScreenshotError as exc:
                print(f"[png] 跳过 PNG 输出：{exc}")
                return html_paths
            return png_paths

        return html_paths

    @staticmethod
    def _parse_ratio(ratio_str: str, width: int, height: int) -> tuple[int, int]:
        """从规格字符串解析出比例分子分母"""
        # 处理复合比例如 "21:9 + 1:1"，取第一个
        first = ratio_str.split("+")[0].split("或")[0].strip()
        if ":" in first:
            parts = first.split(":")
            try:
                return int(parts[0].strip()), int(parts[1].strip())
            except ValueError:
                pass
        # 从实际宽高推算
        from math import gcd

        g = gcd(width, height)
        return width // g, height // g

    @staticmethod
    def list_platforms() -> list[dict]:
        """列出所有支持的平台"""
        return [
            {
                "id": k,
                "name": v["name"],
                "ratio": v["ratio"],
                "dimensions": f"{v['width']}x{v.get('height', v['width'])}",
            }
            for k, v in PLATFORM_SPECS.items()
        ]

    @staticmethod
    def list_styles() -> list[dict]:
        """列出所有视觉风格"""
        return [{"id": k, "bg": v["bg"], "primary": v["primary"], "font": v["font"]} for k, v in STYLE_PRESETS.items()]
