"""杂志风封面生成器

杂志风封面规格：
  - 21:9 主封面（2100×900 逻辑尺寸）
  - 1:1 方图（1080×1080）
  - 深色 Editorial 风格：纸色 #0e0d0c / 墨色 #ece2cf / 点缀 #d4a04a
  - 可参数化：主标题、副标题、kicker、数据条、期号

输出独立 HTML 文件，可在浏览器查看或截图为 PNG。
"""

from __future__ import annotations

import base64 as _b64
import textwrap
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CoverSpec:
    """封面内容规格"""

    title_prefix: str = ""
    title_em: str = ""  # 强调部分（大号 italic）
    title_suffix: str = ""
    kicker: str = ""  # 前缀行（如「开源模型 · 反向出海」）
    subtitle_en: str = ""  # 英文副标（italic）
    lede: str = ""  # 一句导读叙事
    slogan: str = ""  # 底部落款
    issue_no: str = "01"
    issue_date: str = "2026.09"
    # 数据条 4 格：[(num, unit, label), ...]
    data_bar: list[tuple[str, str, str]] = field(default_factory=list)
    # 颜色覆写（可选）
    bg_color: str = "#0e0d0c"
    ink_color: str = "#ece2cf"
    accent_color: str = "#d4a04a"


# ============================================================
# HTML 模板
# ============================================================

COVER_TEMPLATE_WIDE = textwrap.dedent("""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:{bg};">
<section data-vds-schema="v3.1" data-vds-role="cover" data-vds-format="21x9"
  style="width:100%;max-width:2100px;aspect-ratio:21/9;margin:0 auto;
         background-color:{bg};color:{ink};position:relative;overflow:hidden;
         font-family:'Noto Serif SC','Songti SC',Georgia,serif;
         display:block;padding:0;">

  <!-- layer: radial vignette (content-plate 径向暗板) -->
  <div data-vds-layer="field" data-vds-cause="聚焦视觉到中心" style="
    position:absolute;inset:0;z-index:0;
    background:radial-gradient(ellipse 70% 55% at 50% 45%, transparent 40%, {bg} 100%),
               radial-gradient(ellipse 40% 30% at 25% 35%, {accent}22 0%, transparent 60%);
  "></div>

  <!-- layer: paper grain texture (SVG noise 噪点) -->
  <div data-vds-layer="field" data-vds-cause="纸质感" style="
    position:absolute;inset:0;z-index:0;opacity:0.04;mix-blend-mode:overlay;
    background-image:url('data:image/svg+xml;base64,{grain_b64}');
    background-size:200px 200px;
  "></div>

  <!-- layer: ink wash gradient (墨色洗影) -->
  <div data-vds-layer="field" data-vds-cause="层次深度" style="
    position:absolute;inset:0;z-index:0;opacity:0.15;
    background:linear-gradient(135deg, transparent 0%, {ink}08 40%, transparent 70%);
  "></div>

  <!-- watermark 期号 -->
  <span data-vds-layer="material" data-vds-cause="丰富层次" style="
    position:absolute;bottom:-40px;right:60px;font-size:280px;font-style:italic;
    font-family:'Playfair Display',Georgia,serif;font-weight:bold;
    color:{accent};opacity:0.07;letter-spacing:-8px;z-index:1;">{issue_short}</span>

  <!-- 三段式布局：顶部刊头 / 中部标题（垂直居中）/ 底部数据条+口号 -->
  <table style="width:100%;height:100%;border-collapse:collapse;table-layout:fixed;
                position:relative;z-index:2;">

    <!-- top bar: kicker + issue -->
    <tr>
      <td data-vds-layer="inscription"
          style="border:none;padding:48px 80px 0;vertical-align:top;">
        <table style="width:100%;border-collapse:collapse;border:none;"><tr>
          <td style="border:none;padding:0;">
            <span style="font-size:18px;letter-spacing:4px;text-transform:uppercase;
                  color:{accent};font-family:'Noto Sans SC',sans-serif;">{kicker}</span>
          </td>
          <td style="border:none;padding:0;text-align:right;">
            <span style="font-size:16px;color:{ink};opacity:0.6;
                  font-family:'IBM Plex Mono',Menlo,monospace;">ISSUE {issue_no} / {issue_date}</span>
          </td>
        </tr></table>
      </td>
    </tr>

    <!-- main title block（垂直居中，撑满剩余空间） -->
    <tr>
      <td data-vds-layer="event"
          style="border:none;padding:0 80px;vertical-align:middle;height:100%;">
        <h1 style="
          font-size:96px;font-weight:bold;line-height:1.1;margin:0;
          color:{ink};letter-spacing:-2px;">
          {title_prefix}{gap}<em style="color:{accent};font-style:italic;">{title_em}</em>{title_suffix}
        </h1>
        <p style="margin:20px 0 0;font-size:20px;font-style:italic;
           color:{ink};opacity:0.6;font-family:'Playfair Display',Georgia,serif;">{subtitle_en}</p>
        <p style="margin:28px 0 0;font-size:18px;line-height:1.8;
           color:{ink};opacity:0.8;max-width:60%;
           font-family:'Noto Sans SC',sans-serif;">{lede}</p>
      </td>
    </tr>

    <!-- 底部：数据条 + 口号 -->
    <tr>
      <td style="border:none;padding:0 80px 40px;vertical-align:bottom;">
        <div style="display:table;width:100%;border-collapse:collapse;
             border-top:1px solid {ink}55;">
          <div style="display:table-row;">
           {data_bar_cells}
          </div>
        </div>
        <table style="width:100%;border-collapse:collapse;border:none;margin-top:36px;"><tr>
          <td style="border:none;padding:0;">
            <span style="font-size:14px;color:{accent};letter-spacing:3px;
                  font-family:'Noto Sans SC',sans-serif;">{slogan}</span>
          </td>
          <td style="border:none;padding:0;text-align:right;">
            <span style="font-size:14px;color:{ink};opacity:0.4;
                  font-family:'IBM Plex Mono',Menlo,monospace;">{issue_no} / {issue_date}</span>
          </td>
        </tr></table>
      </td>
    </tr>

  </table>
</section>
</body>
</html>
""")

COVER_TEMPLATE_SQUARE = textwrap.dedent("""\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} (方图)</title>
</head>
<body style="margin:0;padding:0;background-color:{bg};">
<section data-vds-schema="v3.1" data-vds-role="cover" data-vds-format="1x1"
  style="width:100%;max-width:1080px;aspect-ratio:1/1;margin:0 auto;
         background-color:{bg};color:{ink};position:relative;overflow:hidden;
         font-family:'Noto Serif SC','Songti SC',Georgia,serif;
         display:block;padding:0;box-sizing:border-box;">

  <!-- layer: radial vignette -->
  <div data-vds-layer="field" style="
    position:absolute;inset:0;z-index:0;
    background:radial-gradient(circle 60% at 50% 40%, transparent 30%, {bg} 95%),
               radial-gradient(circle 35% at 30% 30%, {accent}18 0%, transparent 60%);
  "></div>

  <!-- layer: paper grain -->
  <div data-vds-layer="field" style="
    position:absolute;inset:0;z-index:0;opacity:0.04;mix-blend-mode:overlay;
    background-image:url('data:image/svg+xml;base64,{grain_b64}');
    background-size:180px 180px;
  "></div>

  <!-- layer: ink wash -->
  <div data-vds-layer="field" style="
    position:absolute;inset:0;z-index:0;opacity:0.12;
    background:linear-gradient(160deg, transparent 0%, {ink}08 50%, transparent 80%);
  "></div>

  <!-- watermark -->
  <span data-vds-layer="material" style="
    position:absolute;bottom:-30px;right:30px;font-size:200px;font-style:italic;
    font-family:'Playfair Display',Georgia,serif;font-weight:bold;
    color:{accent};opacity:0.07;z-index:1;">{issue_short}</span>

  <!-- 三段式布局：顶部栏目 / 中部标题（垂直居中）/ 底部数据条+口号 -->
  <table style="width:100%;height:100%;border-collapse:collapse;table-layout:fixed;
                position:relative;z-index:2;">

    <!-- kicker -->
    <tr>
      <td data-vds-layer="inscription" style="border:none;padding:80px 72px 0;vertical-align:top;">
        <span style="font-size:22px;letter-spacing:4px;text-transform:uppercase;
              color:{accent};font-family:'Noto Sans SC',sans-serif;">{kicker}</span>
      </td>
    </tr>

    <!-- 标题块（垂直居中，撑满剩余空间） -->
    <tr>
      <td data-vds-layer="event" style="border:none;padding:0 72px;vertical-align:middle;height:100%;">
        <h1 style="
          font-size:72px;font-weight:bold;line-height:1.1;margin:0;
          color:{ink};letter-spacing:-2px;">
          {title_prefix}{gap}<em style="color:{accent};font-style:italic;">{title_em}</em>{title_suffix}
        </h1>
        <p style="font-size:18px;font-style:italic;color:{ink};opacity:0.5;
           font-family:'Playfair Display',Georgia,serif;margin:24px 0 0;">{subtitle_en}</p>
      </td>
    </tr>

    <!-- 底部：数据条 + 口号 -->
    <tr>
      <td style="border:none;padding:0 72px 80px;vertical-align:bottom;">
        <div style="display:table;width:100%;border-collapse:collapse;
             border-top:1px solid {ink}55;padding-top:24px;">
          <div style="display:table-row;">
           {data_bar_cells_sq}
          </div>
        </div>
        <p style="margin:40px 0 0;font-size:14px;
           color:{accent};letter-spacing:3px;font-family:'Noto Sans SC',sans-serif;">{slogan}</p>
      </td>
    </tr>

  </table>
</section>
</body>
</html>
""")

# SVG 噪点纹理（用于 paper grain 层）
# 一个基于 feTurbulence 的微型 SVG，base64 编码内嵌

_GRAIN_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
    '<filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.65" '
    'numOctaves="3" stitchTiles="stitch"/></filter>'
    '<rect width="100%" height="100%" filter="url(#n)"/></svg>'
)
GRAIN_B64 = _b64.b64encode(_GRAIN_SVG.encode()).decode("ascii")


class CoverGenerator:
    """杂志风封面生成器

    用法：
        gen = CoverGenerator()
        spec = CoverSpec(
            title_prefix="最懂", title_em="生活", title_suffix="的 AI",
            kicker="开源模型 · 反向出海",
            ...
        )
        gen.generate(spec, output_dir=Path("./covers"))
    """

    def generate(self, spec: CoverSpec, output_dir: Path, png: bool = False) -> tuple[Path, Path]:
        """生成 21:9 + 1:1 两份封面 HTML（可选 PNG 截图）

        Returns: (wide_path, square_path) — HTML 或 PNG（当 png=True 时）
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # 数据条 cells（配色跟随封面 accent / ink）
        data_cells_wide = self._render_data_bar(
            spec.data_bar,
            square=False,
            accent=spec.accent_color,
            ink=spec.ink_color,
        )
        data_cells_sq = self._render_data_bar(
            spec.data_bar,
            square=True,
            accent=spec.accent_color,
            ink=spec.ink_color,
        )

        issue_short = spec.issue_no.lstrip("0") or "0"
        title_display = f"{spec.title_prefix}{spec.title_em}{spec.title_suffix}".strip() or "Untitled"
        # 前缀和强调部分之间插入空格（如果两者都有值）
        gap = " " if (spec.title_prefix.strip() and spec.title_em.strip()) else ""

        common = dict(
            bg=spec.bg_color,
            ink=spec.ink_color,
            accent=spec.accent_color,
            kicker=spec.kicker,
            title_prefix=spec.title_prefix,
            title_em=spec.title_em,
            title_suffix=spec.title_suffix,
            gap=gap,
            subtitle_en=spec.subtitle_en,
            lede=spec.lede,
            slogan=spec.slogan,
            issue_no=spec.issue_no,
            issue_date=spec.issue_date,
            issue_short=issue_short,
            data_bar_cells=data_cells_wide,
            data_bar_cells_sq=data_cells_sq,
            grain_b64=GRAIN_B64,
            title=title_display,
        )

        wide_html = COVER_TEMPLATE_WIDE.format(**common)
        square_html = COVER_TEMPLATE_SQUARE.format(**common)

        wide_html_path = output_dir / f"cover_{spec.issue_no}_21x9.html"
        square_html_path = output_dir / f"cover_{spec.issue_no}_1x1.html"
        wide_html_path.write_text(wide_html, encoding="utf-8")
        square_html_path.write_text(square_html, encoding="utf-8")

        if png:
            from .screenshot import ScreenshotError, Screenshotter

            wide_png = output_dir / f"cover_{spec.issue_no}_21x9.png"
            square_png = output_dir / f"cover_{spec.issue_no}_1x1.png"
            try:
                shooter = Screenshotter()
                shooter.capture(wide_html_path, wide_png, 2100, 900)
                shooter.capture(square_html_path, square_png, 1080, 1080)
            except ScreenshotError as exc:
                print(f"[png] 跳过 PNG 输出：{exc}")
                return wide_html_path, square_html_path
            return wide_png, square_png

        return wide_html_path, square_html_path

    def _render_data_bar(
        self,
        data: list[tuple[str, str, str]],
        square: bool = False,
        accent: str = "#d4a04a",
        ink: str = "#ece2cf",
    ) -> str:
        """渲染数据条 4 格（配色跟随封面 accent / ink，不硬编码）"""
        if not data:
            return ""
        cells: list[str] = []
        for i, (num, unit, label) in enumerate(data[:4]):
            is_first = i == 0
            color = accent if is_first else ink
            num_size = "36px" if not square else "28px"
            label_size = "13px" if not square else "12px"
            unit_str = f' <span style="font-size:14px;">{unit}</span>' if unit else ""
            cells.append(
                f'<span style="display:table-cell;padding:20px 24px 0 0;vertical-align:top;">'
                f'<span style="font-size:{num_size};font-weight:bold;color:{color};'
                f"font-family:'Playfair Display',Georgia,serif;\">{num}{unit_str}</span>"
                f'<br/><span style="font-size:{label_size};color:{ink};opacity:0.72;'
                f"font-family:'Noto Sans SC',sans-serif;\">{label}</span></span>"
            )
        return "".join(cells)
