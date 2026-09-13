# Examples

This directory contains sample outputs from inkwell.

## Directory Structure

```
examples/
├── README.md              ← this file
├── article.md             ← sample Markdown input
├── output/                ← sample pipeline output
│   ├── article_preview.html          ← publish version (CDN images)
│   ├── article_preview_local.html    ← local preview version (base64 images)
│   └── article_validated.txt         ← validator report
├── covers/                ← sample magazine covers
│   ├── cover_21x9.html    ← 21:9 main cover
│   ├── cover_1x1.html     ← 1:1 square cover
│   ├── cover_21x9.png     ← PNG screenshot (21:9)
│   └── cover_1x1.png      ← PNG screenshot (1:1)
├── cards/                 ← sample social cards
│   ├── xhs_cover.html     ← Xiaohongshu cover (3:4)
│   ├── xhs_page_2.html    ← Xiaohongshu content page
│   ├── xhs_page_3.html    ← Xiaohongshu content page
│   └── xhs_cover.png      ← PNG screenshot
└── screenshots/           ← demo GIFs for README
    ├── pipeline_demo.gif  ← end-to-end demo
    └── cover_demo.gif     ← cover generation demo
```

## How to Reproduce

```bash
# Generate all examples from the sample article
inkwell run examples/article.md -o examples/output --theme moyu-green

# Generate magazine covers
inkwell cover \
  --title "最懂" --title-em "生活" --kicker "开源 · 出海" \
  --subtitle-en "When AI meets life." \
  --lede "一句话导读叙事。" \
  --slogan "探索前沿" \
  --issue 09 --date 2026.09 \
  -o examples/covers/ --png

# Generate Xiaohongshu cards
inkwell card \
  --platform xhs --style editorial \
  --pages 3 --brand "作者" --tag "#AI工具" \
  --titles "封面标题" "核心要点" "总结" \
  -o examples/cards/ --png
```

## Contributing Examples

If you have a great example output, please submit a PR adding it to this directory. GIFs and screenshots are especially welcome — they help new users understand what the pipeline produces.
