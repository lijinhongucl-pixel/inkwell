"""CLI 入口

用法：
    inkwell run article.md --theme moyu-green
    inkwell search "AI agent" --source github --limit 10
    inkwell generate "Docker 优化" --style tutorial
    inkwell cover --title "标题" --kicker "前缀·后缀"
    inkwell card --platform xhs --style swiss --pages 5
    inkwell audit output/cover_01_21x9.html --type cover
    inkwell advise --topic "Docker 优化" --type tutorial
    inkwell validate preview.html
    inkwell themes
    inkwell wordcheck article.md
    inkwell stats article.md
    inkwell toc article.md
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .core import Pipeline, PipelineConfig
from .social_card import PLATFORM_SPECS, STYLE_PRESETS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="inkwell",
        description="内容发布流水线：Markdown→公众号HTML→图片处理→CDN",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # --- run ---
    run = sub.add_parser("run", help="执行完整流水线")
    run.add_argument("input", type=Path, help="Markdown 文件路径")
    run.add_argument("-o", "--output", type=Path, default=Path("./output"), help="输出目录")
    run.add_argument("--theme", default="moyu-green")
    run.add_argument("--quality", type=int, default=82, help="JPEG 质量 1-100")
    run.add_argument("--max-width", type=int, default=600, help="图片最大宽度")
    run.add_argument("--subdir", default="", help="CDN 子目录")
    run.add_argument(
        "--github-repo",
        default=os.getenv("INKWELL_GITHUB_REPO", ""),
        help="图片仓库 owner/repo（需与 --cdn-base、GITHUB_TOKEN 同时提供才会走 CDN 上传）",
    )
    run.add_argument(
        "--cdn-base",
        default=os.getenv("INKWELL_CDN_BASE", ""),
        help="图片外链前缀，如 https://cdn.jsdelivr.net/gh/owner/repo@main",
    )
    run.add_argument("--no-upload", action="store_true", help="跳过 CDN 上传（降级为 base64）")
    run.add_argument("--no-local-preview", action="store_true", help="不生成 base64 本地预览版")
    run.add_argument(
        "--no-embed-external",
        action="store_true",
        help="不把正文里的外链图下载内嵌进本地预览版（离线预览会裂图）",
    )
    run.add_argument("--no-validate", action="store_true", help="跳过兼容性校验")

    # --- search ---
    search = sub.add_parser("search", help="内容搜索，发现选题灵感和参考素材")
    search.add_argument("query", help="搜索关键词")
    search.add_argument(
        "--source", default="github", choices=["github", "web", "custom"], help="搜索来源（默认 github）"
    )
    search.add_argument("--limit", type=int, default=10, help="最大结果数")
    search.add_argument("--backend", default=None, help="自定义搜索 API 地址")
    search.add_argument("--markdown", action="store_true", help="输出 Markdown 表格格式")
    search.add_argument("-o", "--output", type=Path, default=None, help="保存结果到文件")

    # --- generate ---
    gen = sub.add_parser("generate", help="生成 Markdown 草稿（供 Agent 调用）")
    gen.add_argument("topic", help="文章主题/标题")
    gen.add_argument(
        "--style",
        default="general",
        choices=["tutorial", "review", "analysis", "opinion", "general"],
        help="文章风格类型",
    )
    gen.add_argument("--outline", action="store_true", help="只生成大纲不展开正文")
    gen.add_argument("--search", action="store_true", help="自动搜索素材填充草稿")
    gen.add_argument("--search-source", default="github", choices=["github", "web", "custom"])
    gen.add_argument("--search-limit", type=int, default=5, help="搜索结果数量")
    gen.add_argument("-o", "--output", type=Path, default=None, help="保存路径（默认 stdout）")

    # --- validate ---
    val = sub.add_parser("validate", help="扫描已有 HTML 的公众号兼容性")
    val.add_argument("html", type=Path)

    # --- themes ---
    sub.add_parser("themes", help="列出所有可用排版主题")

    # --- cover ---
    cover = sub.add_parser("cover", help="生成杂志风封面（21:9 + 1:1）")
    cover.add_argument("--title", required=True, help="封面主标题")
    cover.add_argument("--title-em", default="", help="标题强调部分（italic + accent 色）")
    cover.add_argument("--kicker", default="", help="前缀行（如「开源模型 · 反向出海」）")
    cover.add_argument("--subtitle-en", default="", help="英文副标")
    cover.add_argument("--lede", default="", help="一句导读叙事")
    cover.add_argument("--slogan", default="", help="底部落款")
    cover.add_argument("--issue", default="01", help="期号")
    cover.add_argument("--date", default="2026.09", help="日期")
    cover.add_argument("--data", nargs="*", default=[], help="数据条，格式 num:unit:label（可多组）")
    cover.add_argument("-o", "--output", type=Path, default=Path("./covers"), help="输出目录")
    cover.add_argument("--png", action="store_true", help="同时输出 PNG 截图（需 Playwright）")

    # --- card ---
    card = sub.add_parser("card", help="生成社交卡片（小红书轮播等）")
    card.add_argument("--platform", default="xhs", choices=list(PLATFORM_SPECS.keys()))
    card.add_argument("--style", default="swiss", choices=list(STYLE_PRESETS.keys()))
    card.add_argument("--pages", type=int, default=3, help="卡片页数（含封面）")
    card.add_argument("--brand", default="", help="品牌/作者署名")
    card.add_argument("--tag", default="", help="标签（如 #AI工具）")
    card.add_argument("--titles", nargs="*", default=[], help="各页标题（空格分隔）")
    card.add_argument("--subtitles", nargs="*", default=[], help="各页副标题（空格分隔）")
    card.add_argument("--bodies", nargs="*", default=[], help="各页正文（空格分隔，每页一段）")
    card.add_argument("-o", "--output", type=Path, default=Path("./cards"), help="输出目录")
    card.add_argument("--png", action="store_true", help="同时输出 PNG 截图（需 Playwright）")

    # --- audit ---
    audit = sub.add_parser("audit", help="三门设计审计（Victor Design System）")
    audit.add_argument("html", type=Path, help="待审计的 HTML 文件")
    audit.add_argument("--type", default="article", choices=["article", "cover"])

    # --- advise ---
    advise = sub.add_parser("advise", help="封面设计建议")
    advise.add_argument("--topic", required=True, help="文章主题/标题")
    advise.add_argument(
        "--type",
        default="general",
        choices=["tutorial", "review", "analysis", "opinion", "list", "comparison", "general"],
    )
    advise.add_argument("--multi", action="store_true", help="输出多个备选建议")

    # --- publish ---
    pub = sub.add_parser("publish", help="发布内容（公众号草稿箱 / 剪贴板）")
    pub.add_argument("html", type=Path, help="要发布的 HTML 文件")
    pub.add_argument(
        "--target", default="clipboard", choices=["clipboard", "wechat"], help="发布目标（默认 clipboard）"
    )
    pub.add_argument("--title", default="", help="文章标题（wechat 模式必填）")
    pub.add_argument("--author", default="", help="作者署名")
    pub.add_argument("--thumb", default="", help="封面图 media_id（已在微信上传的永久素材，二选一）")
    pub.add_argument(
        "--thumb-image", type=Path, default=None, help="封面图本地路径，自动上传拿 media_id（与 --thumb 二选一）"
    )
    pub.add_argument("--digest", default="", help="文章摘要（≤128 字，缺省由微信抓正文前 54 字）")

    # --- wordcheck ---
    wc = sub.add_parser("wordcheck", help="敏感词 / 合规检测")
    wc.add_argument("input", type=Path, help="Markdown 文件路径")
    wc.add_argument("--no-ad-law", action="store_true", help="跳过广告法极限词检测")
    wc.add_argument("--no-platform", action="store_true", help="跳过平台违规词检测")
    wc.add_argument("--no-sensitive", action="store_true", help="跳过通用敏感词检测")
    wc.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # --- stats ---
    stats_parser = sub.add_parser("stats", help="字数统计与阅读时间分析")
    stats_parser.add_argument("input", type=Path, help="Markdown 文件路径")
    stats_parser.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # --- toc ---
    toc_parser = sub.add_parser("toc", help="生成文章目录（TOC 卡片）")
    toc_parser.add_argument("input", type=Path, help="Markdown 文件路径")
    toc_parser.add_argument("--theme", default="moyu-green", help="主题色板（用于目录配色）")
    toc_parser.add_argument("--no-numbers", action="store_true", help="不显示自动编号")
    toc_parser.add_argument("--title", default="目录", help="目录卡片标题")
    toc_parser.add_argument("-o", "--output", type=Path, default=None, help="保存 HTML 到文件")

    return p


def cmd_run(args: argparse.Namespace) -> int:
    cfg = PipelineConfig(
        input_md=args.input.resolve(),
        output_dir=args.output.resolve(),
        theme=args.theme,
        image_quality=args.quality,
        image_max_width=args.max_width,
        image_subdir=args.subdir,
        github_repo=args.github_repo,
        cdn_base=args.cdn_base,
        github_token=os.getenv("GITHUB_TOKEN") if not args.no_upload else None,
        embed_external=not args.no_embed_external,
        emit_local_preview=not args.no_local_preview,
        strict_copy_compat=not args.no_validate,
    )
    pipe = Pipeline(cfg)
    result = pipe.run()

    print(f"发布版: {result.publish_html}")
    if result.local_html:
        print(f"本地版: {result.local_html}")
    if result.uploaded_images:
        print(f"处理图片 {len(result.uploaded_images)} 张")
    if result.external_embedded_images:
        print(f"[图片] 本地预览版已内嵌 {result.external_embedded_images} 张外链图")
    if any(u.startswith("data:") for u in result.uploaded_images):
        cdn_ready = bool(args.github_repo and args.cdn_base and os.getenv("GITHUB_TOKEN"))
        if not cdn_ready:
            print(
                "[提示] 图片以内嵌 base64 输出。要让发布版改用 CDN 外链，"
                "请同时提供 --github-repo、--cdn-base 与 GITHUB_TOKEN 环境变量。"
            )
    for w in result.image_warnings:
        print(f"[图片] {w}")
    for w in result.compat_warnings:
        print(w)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    from .searcher import ContentSearcher

    searcher = ContentSearcher()
    results = searcher.search(
        query=args.query,
        source=args.source,
        limit=args.limit,
        backend=args.backend,
    )
    if args.markdown:
        output_text = ContentSearcher.to_markdown(results, title=f"搜索: {args.query}")
    else:
        output_text = "\n".join(str(r) for r in results) if results else "无结果。"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
        print(f"保存到: {args.output}")
    else:
        print(output_text)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    from .generator import DraftGenerator

    gen = DraftGenerator()
    if args.search:
        md = gen.generate_with_search(
            topic=args.topic,
            style=args.style,
            search_source=args.search_source,
            search_limit=args.search_limit,
            outline_only=args.outline,
        )
    else:
        md = gen.generate(topic=args.topic, style=args.style, outline_only=args.outline)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(md, encoding="utf-8")
        print(f"草稿已保存: {args.output}")
    else:
        print(md)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from .processors.validator import CopyCompatValidator

    warnings = CopyCompatValidator().scan(args.html.resolve())
    if warnings:
        for w in warnings:
            print(w)
        return 1
    print("兼容性校验通过")
    return 0


def cmd_themes() -> int:
    from .processors.markdown_proc import THEME_META

    print(f"{'ID':<20} {'名称':<12} 适用场景")
    print("-" * 60)
    for t in THEME_META:
        print(f"{t['id']:<20} {t['name']:<12} {t['desc']}")
    return 0


def _parse_data_bar(s: str) -> tuple[str, str, str]:
    """解析数据条参数，支持 'num:unit:label' 或 'num:label' 格式"""
    parts = s.split(":")
    if len(parts) >= 3:
        return (parts[0], parts[1], parts[2])
    elif len(parts) == 2:
        return (parts[0], "", parts[1])
    else:
        return (parts[0], "", "")


def cmd_cover(args: argparse.Namespace) -> int:
    from .cover_gen import CoverGenerator, CoverSpec

    spec = CoverSpec(
        title_prefix=args.title,
        title_em=args.title_em,
        kicker=args.kicker,
        subtitle_en=args.subtitle_en,
        lede=args.lede,
        slogan=args.slogan,
        issue_no=args.issue,
        issue_date=args.date,
        data_bar=[_parse_data_bar(d) for d in args.data if ":" in d],
    )
    gen = CoverGenerator()
    wide, square = gen.generate(spec, output_dir=args.output.resolve(), png=args.png)
    print(f"21:9 封面: {wide}")
    print(f"1:1 方图:  {square}")
    return 0


def cmd_card(args: argparse.Namespace) -> int:
    from .social_card import CardPage, CardSpec, SocialCardGenerator

    pages = []
    for i in range(args.pages):
        title = args.titles[i] if i < len(args.titles) else f"第{i + 1}页"
        subtitle = args.subtitles[i] if i < len(args.subtitles) else ""
        body = args.bodies[i] if i < len(args.bodies) else ""
        pages.append(CardPage(title=title, subtitle=subtitle, body=body, page_num=i + 1))
    spec = CardSpec(
        platform=args.platform,
        style=args.style,
        pages=pages,
        brand=args.brand,
        tag=args.tag,
    )
    gen = SocialCardGenerator()
    paths = gen.generate(spec, output_dir=args.output.resolve(), png=args.png)
    print(f"生成 {len(paths)} 张卡片:")
    for p in paths:
        print(f"  {p}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    from .design_audit import DesignAuditor

    auditor = DesignAuditor()
    if args.type == "cover":
        report = auditor.audit_html_cover(args.html.resolve())
    else:
        report = auditor.audit_html_article(args.html.resolve())
    print(report.summary())
    return 0 if report.all_passed else 1


def cmd_advise(args: argparse.Namespace) -> int:
    from .cover_advisor import CoverAdvisor

    advisor = CoverAdvisor()
    if args.multi:
        results = advisor.advise_multi(topic=args.topic, article_type=args.type)
        print(f"=== 封面设计建议（{len(results)} 个备选）===\n")
        for i, r in enumerate(results, 1):
            print(f"--- 方案 {i}: {r.pattern_name} ---")
            print(f"说明: {r.description}")
            print(f"配色: {r.color_suggestion}")
            print(f"布局: {r.layout_hint}")
            print(f"标题技巧: {'、'.join(r.title_tips)}")
            print(f"避免: {'、'.join(r.avoid)}")
            print()
    else:
        r = advisor.advise(topic=args.topic, article_type=args.type)
        print("=== 封面设计建议 ===\n")
        print(f"模式: {r.pattern_name}")
        print(f"说明: {r.description}")
        print(f"配色: {r.color_suggestion}")
        print(f"布局: {r.layout_hint}")
        print("标题技巧:")
        for t in r.title_tips:
            print(f"  - {t}")
        print("避免:")
        for a in r.avoid:
            print(f"  ! {a}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    from .publisher import Publisher

    publisher = Publisher()
    if args.target == "wechat":
        result = publisher.publish_to_wechat(
            html_path=args.html.resolve(),
            title=args.title or args.html.stem,
            author=args.author,
            thumb_media_id=args.thumb,
            thumb_image=args.thumb_image,
            digest=args.digest,
        )
    else:
        result = publisher.publish_to_clipboard(args.html.resolve())
    # 逐条告警必须在成功/失败之前打出来：图片没转存成功时草稿里会缺图，
    # 只报「推送成功」会让用户以为万事大吉
    for w in result.warnings:
        print(f"[{result.platform}] 警告: {w}")
    if result.images_total:
        print(f"[{result.platform}] 正文图片: {result.images_transferred}/{result.images_total} 张已转存到微信图床")
    if result.success:
        print(f"[{result.platform}] {result.message}")
        if result.media_id:
            print(f"media_id: {result.media_id}")
        return 0
    else:
        print(f"[{result.platform}] 失败: {result.message}")
        return 1


def cmd_wordcheck(args: argparse.Namespace) -> int:
    from .wordcheck import WordChecker

    text = args.input.read_text(encoding="utf-8")
    checker = WordChecker(
        check_ad_law=not args.no_ad_law,
        check_platform=not args.no_platform,
        check_sensitive=not args.no_sensitive,
    )
    report = checker.check(text)

    if args.json:
        import json

        data = {
            "risk_level": report.risk_level,
            "total_scanned": report.total_scanned,
            "hits_count": len(report.hits),
            "hits": [
                {
                    "word": h.word,
                    "suggestion": h.suggestion,
                    "category": h.category,
                    "line": h.line_num,
                }
                for h in report.hits
            ],
        }
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(report.summary())

    return 0 if report.is_clean else 1


def cmd_stats(args: argparse.Namespace) -> int:
    from .stats import ArticleAnalyzer

    text = args.input.read_text(encoding="utf-8")
    analyzer = ArticleAnalyzer()
    stats = analyzer.analyze(text)

    if args.json:
        import json

        print(json.dumps(stats.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(stats.summary())
    return 0


def cmd_toc(args: argparse.Namespace) -> int:
    from .processors.markdown_proc import THEMES
    from .toc import TOCGenerator

    text = args.input.read_text(encoding="utf-8")
    theme_colors = THEMES.get(args.theme, THEMES["moyu-green"])

    gen = TOCGenerator()
    result = gen.generate(
        text,
        theme_colors=theme_colors,
        show_numbers=not args.no_numbers,
        title=args.title,
    )

    if result.is_empty:
        print("文章中没有 H2/H3 标题，无法生成目录。")
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.html, encoding="utf-8")
        print(f"目录已保存: {args.output}（{result.count} 个标题）")
    else:
        print(result.html)
    print(f"\n（提取到 {result.count} 个标题）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "search":
        return cmd_search(args)
    elif args.command == "generate":
        return cmd_generate(args)
    elif args.command == "cover":
        return cmd_cover(args)
    elif args.command == "card":
        return cmd_card(args)
    elif args.command == "audit":
        return cmd_audit(args)
    elif args.command == "advise":
        return cmd_advise(args)
    elif args.command == "publish":
        return cmd_publish(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "themes":
        return cmd_themes()
    elif args.command == "wordcheck":
        return cmd_wordcheck(args)
    elif args.command == "stats":
        return cmd_stats(args)
    elif args.command == "toc":
        return cmd_toc(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
