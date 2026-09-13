<div align="center">

# Inkwell

**The only CLI that takes you from idea to published — not just formatting.**

Markdown → WeChat HTML → Magazine Cover → Social Cards → Publish.

<!-- CI 状态徽章，直接读 .github/workflows/ci.yml 在 main 上的最近一次运行结果 -->
[![CI](https://github.com/lijinhongucl-pixel/inkwell/actions/workflows/ci.yml/badge.svg)](https://github.com/lijinhongucl-pixel/inkwell/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-multi--stage-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Version](https://img.shields.io/badge/version-0.7.9-green.svg)](./CHANGELOG.md)

[English](#english) | [中文](#中文)

</div>

---

> **⚠️ 本项目的 PyPI 发行名是 `inkwell-press`，不是 `inkwell`**
>
> - `pip install inkwell` → 装到无关的 **Qt 深色主题**（[pkkid/python-inkwell](https://github.com/pkkid/python-inkwell)）
> - `pip install inkwell-cli` → 装到无关的 **播客转 Markdown 笔记工具**（[chekos/inkwell-cli](https://github.com/chekos/inkwell-cli)）。该项目的导入包名与命令名也叫 `inkwell`，**不要与本项目装进同一个 Python 环境**
>
> ✅ 本项目的发行名是 `inkwell-press`（**尚未上传 PyPI**，当前请从源码安装，见[安装](#安装)一节）

## 中文

### 你是不是也经历过这种痛苦

```
写完文章 → 手动排版 30 分钟 → 粘贴公众号 → 样式全崩 → 重新调 →
再粘贴 → 代码块乱了 → 又调 → 找封面图 → 翻素材库 → 不够好看 →
用 Canva 做 → 导出 → 手动传 → 再写小红书 → 又排一遍……
```

**一次内容发布，平均花在「排版和视觉」上的时间超过 1 小时。**

Inkwell 把这整个流程压成一条命令。

```bash
inkwell run article.md              # 排版 + 图片处理 + 校验
inkwell cover --title "标题" --png    # 杂志封面 + PNG
inkwell card --platform xhs --png    # 小红书卡片 + PNG
inkwell publish --target clipboard   # 复制到剪贴板，粘贴即发
```

### 和其他工具的区别

市面已有优秀的排版工具（doocs/md 11.7k stars、mdnice、xiaohu-wechat-format），但它们都只解决「排版」这一个环节。**Inkwell 是唯一覆盖全链路的 CLI**：

| 能力 | doocs/md | mdnice | xiaohu-wechat-format | **Inkwell** |
|------|:--------:|:------:|:--------------------:|:-----------:|
| Markdown → 公众号 HTML | Web 应用 | Web 应用 | Python CLI | **Python CLI** |
| 排版主题数 | 30+ | 20+ | 30 | 15（持续扩展） |
| 杂志封面生成 | Docker 部署 | 无 | Gemini API | **内置（无需 AI API）** |
| 封面设计建议 | 无 | 无 | 无 | **6 种高转化模式智能推荐** |
| 小红书社交卡片 | 无 | 无 | 无 | **11 平台覆盖（含 IG/X/LinkedIn/Pinterest/YT）** |
| PNG 截图输出 | 无 | 无 | 无 | **Playwright 2x Retina** |
| 设计质量审计 | 无 | 无 | 无 | **三门审计（主题/密度/交付）** |
| 敏感词 / 合规检测 | 无 | 无 | 无 | **广告法极限词 + 平台违规词 + 通用敏感词** |
| 文章目录 TOC | 无 | 无 | 无 | **自动提取 H2/H3 + 编号 + 公众号兼容卡片** |
| 字数统计 / 阅读时间 | 无 | 无 | 无 | **中英分开计数 + 阅读时长 + 结构分析** |
| 选题搜索 | 无 | 无 | 无 | **GitHub trending + 自定义后端** |
| 草稿骨架生成 | 无 | 无 | 无 | **5 种风格 + 搜索自动填充** |
| 公众号草稿箱推送 | 无 | 无 | 有 | **有** |
| 剪贴板一键复制 | 手动 | 手动 | 无 | **有** |
| AI Agent 集成 | 无 | 无 | Claude Code | **任何 Agent（通用 Skill）** |
| Docker 多阶段 | 有 | 无 | 无 | **有（120MB）** |
| 形态 | Web 编辑器 | Web + 商业化 | Python 脚本 | **Python CLI + Docker + Skill** |

**一句话总结区别**：它们是「排版器」，Inkwell 是「出版流水线」。

### 核心 CLI 命令一览

| 命令 | 用途 |
|------|------|
| `inkwell run article.md` | 完整流水线：排版 + 图片处理 + 校验 |
| `inkwell search "AI工具"` | 搜索选题灵感（GitHub trending / web） |
| `inkwell generate "主题" --search` | 自动生成 Markdown 草稿（接搜索自动填充） |
| `inkwell cover --png` | 杂志封面生成 + PNG 截图 |
| `inkwell card --png` | 社交卡片生成 + PNG 截图 |
| `inkwell audit output/cover.html` | 设计质量审计 |
| `inkwell advise --topic "..."` | 封面设计建议 |
| `inkwell publish output/article.html` | 发布（剪贴板 / 公众号草稿箱） |
| `inkwell wordcheck article.md` | 敏感词 / 合规检测（广告法 + 平台违规 + 通用敏感） |
| `inkwell stats article.md` | 字数统计 + 阅读时间 + 结构分析 |
| `inkwell toc article.md` | 自动生成文章目录卡片（H2/H3 提取 + 编号） |
| `inkwell validate output/article.html` | 兼容性校验 |
| `inkwell themes` | 列出可用主题 |

### 安装

```bash
# 从源码安装（当前可用）
git clone https://github.com/lijinhongucl-pixel/inkwell.git
cd inkwell
pip install -e .
pip install -e ".[dev]"      # 要跑测试或 lint 时才需要

# Docker
docker build -t inkwell .
```

#### 从 PyPI 安装（发行名 `inkwell-press`，**尚未发布**）

```bash
pip install inkwell-press
```

**为什么发行名和命令名不一样**：PyPI 上的 `inkwell` 已被一个无关的 Qt 主题占用，
所以本项目的发行名定为 `inkwell-press`；装好之后导入包名与命令行都还是 `inkwell`。

⚠️ **这个发行包目前还没有上传到 PyPI**，上面那行现在执行会报
`No matching distribution found`。请先用上面的源码方式安装。

#### 可选：PNG 截图支持

`--png` 参数需要 Playwright，**不装也能用**——所有命令都会正常输出 HTML，
只是跳过 PNG 并给出提示。

```bash
npm install -g playwright-core
npx playwright install chromium

# 使用已有环境（自定义 node_modules 或浏览器路径）
export PLAYWRIGHT_NODE_PATH=/path/to/node_modules
export PLAYWRIGHT_CHROMIUM_PATH=/path/to/chrome-headless-shell
```

### 快速开始

```bash
# 完整流水线
inkwell run article.md -o ./output --theme moyu-green

# 搜索选题
inkwell search "AI agent" --limit 10

# 生成草稿（自动搜索填充）
inkwell generate "Docker 镜像优化" --style tutorial --search --limit 5

# 杂志封面 + PNG
inkwell cover \
  --title "最懂" --title-em "生活" --kicker "开源 · 出海" \
  --subtitle-en "When AI meets life." \
  --lede "一句话导读叙事。" \
  --slogan "探索前沿" \
  --issue 09 --date 2026.09 \
  -o ./covers/ --png

# 小红书 3 页轮播 + PNG
inkwell card \
  --platform xhs --style editorial \
  --pages 3 --brand "作者" --tag "#AI工具" \
  --titles "封面标题" "核心要点" "总结" \
  -o ./cards/ --png

# 发布到剪贴板（以富文本写入，粘贴到公众号即为排版后的效果）
inkwell publish output/article_preview.html --target clipboard

# 发布到公众号草稿箱（需配置 APP_ID / APP_SECRET，封面需先上传拿到 media_id）
inkwell publish output/article_preview.html \
  --target wechat --title "文章标题" --author "作者" --thumb <封面 media_id>

# 只做兼容性校验
inkwell validate output/article_preview.html
```

> **关于两版产出**：`run` 会同时生成 `_预览.html`（发布版，图片走 CDN 外链，
> 用于复制到公众号）和 `_预览_本地版.html`（图片内嵌 base64，用于 IDE 预览面板
> 等加载不了外网的环境）。两版正文完全一致，只有图片承载方式不同。
>
> **要拿到 CDN 外链，三项配置缺一不可**：`GITHUB_TOKEN` 环境变量、
> `--github-repo owner/repo`、`--cdn-base <外链前缀>`。缺任一项，图片都会降级为
> 内嵌 base64（此时两版内容相同），命令行会直接提示你还缺什么。
>
> ```bash
> export GITHUB_TOKEN=ghp_xxx
> inkwell run article.md \
>   --github-repo your-name/your-image-repo \
>   --cdn-base https://cdn.jsdelivr.net/gh/your-name/your-image-repo@main \
>   --subdir my-article
> ```
>
> ⚠️ 含内嵌 base64 的 HTML **不要直接粘进公众号编辑器**——图片会变乱码。请按上面的
> 方式配好外链，或在浏览器里打开该 HTML 全选复制。

> **平台支持（重要）**：`--target clipboard` 写入**富文本**依赖系统能力 ——
> macOS 走 AppleScript 写入 `«class HTML»` flavor；Linux 走 `xclip`
> （需 `apt install xclip`）。**Windows 目前没有富文本剪贴板实现**：
> 会降级为纯文本并明确提示，直接粘贴到公众号只能得到无格式文字。
> Windows 用户请改为在浏览器打开 `_预览.html` → 全选 → 复制。
> 其余功能（排版、封面、社交卡片、兼容性校验、字数统计）三平台行为一致。


### Docker

```bash
# 把 Markdown 放进 ./input，产出在 ./output
docker compose run --rm pipeline run /app/input/article.md -o /app/output
```

### Python SDK

```python
from inkwell import Pipeline, PipelineConfig
from pathlib import Path

cfg = PipelineConfig(
    input_md=Path("article.md"),
    output_dir=Path("./output"),
    theme="moyu-green",
    cdn_base="https://cdn.example.com/images",
    github_repo="your-org/your-image-repo",
)
result = Pipeline(cfg).run()
print(result.publish_html)
```

### 主题系统

内置 15 套排版主题，覆盖从科技到生活、从商务到创意的全场景：

| 主题 | 主色 | 适用场景 |
|------|------|---------|
| `moyu-green` 摸鱼绿 | `#059669` | 教程、测评、清单（默认推荐） |
| `red-white` 红白色系 | `#DC2626` | 深度分析、观点、力量感话题 |
| `graphite-minimal` 石墨极简 | `#52525B` | 设计、科技评论、专业观点 |
| `zen-whitespace` 留白禅意 | `#4A5D52` | 禅意、极简生活、深度随笔 |
| `moyu-ticket` 摸鱼票据 | `#059669` | 测评、工具对比（票据视觉隐喻） |
| `olive-journal` 橄榄手记 | `#1E1F23` | 内刊手记、深度评测、案例复盘 |
| `classic-serif` 经典衬线 | `#1B3A2E` | 深度长文、编辑部风格 |
| `cyber-neon` 赛博霓虹 | `#00F0FF` | 科技、AI、编程、暗色酷炫 |
| `coffee-mocha` 咖啡摩卡 | `#6F4E37` | 生活、美食、旅行、暖调随笔 |
| `ocean-blue` 海洋蓝 | `#0066CC` | 商务、财经、行业分析、职场 |
| `sunset-warm` 日落暖橙 | `#E76F51` | 生活方式、品牌故事、情感 |
| `ink-wash` 水墨山水 | `#1A1A1A` | 传统文化、诗词、人文历史 |
| `forest-deep` 森林深绿 | `#2D6A4F` | 环保、自然、可持续发展、健康 |
| `royal-purple` 皇家紫 | `#6A1B9A` | 创意、设计、艺术、灵感 |
| `sakura-pink` 樱花粉 | `#E91E63` | 时尚、美妆、穿搭、少女心 |

#### 自定义主题

```python
from inkwell.processors.markdown_proc import MarkdownProcessor, THEMES

THEMES["my-brand"] = {
    "bg": "#FFFFFF", "text": "#333333",
    "primary": "#0066CC", "accent": "#FF6600",
    "highlight": "#CC0000", "font": "Georgia, serif",
}
proc = MarkdownProcessor(theme="my-brand")
```

### 社交卡片

11 个平台，中文 + 海外全覆盖：

**中文平台**

| 平台 | 比例 | 尺寸 |
|------|------|------|
| `xhs` 小红书 | 3:4 | 1080×1440 |
| `wechat-cover` 公众号 | 21:9 + 1:1 | 2100×900 + 1080×1080 |
| `wechat-article` 正文 | 16:9 | 1920×1080 |
| `weibo` 微博 | 1:1 | 1080×1080 |

**海外平台**

| 平台 | 比例 | 尺寸 |
|------|------|------|
| `instagram-feed` IG Feed | 1:1 | 1080×1080 |
| `instagram-story` IG Story / Reels | 9:16 | 1080×1920 |
| `x-twitter` X (Twitter) | 16:9 | 1600×900 |
| `linkedin` LinkedIn | 1.91:1 | 1200×627 |
| `pinterest` Pinterest | 2:3 | 1000×1500 |
| `youtube-thumb` YouTube | 16:9 | 1280×720 |

```bash
# Instagram Feed 轮播
inkwell card --platform instagram-feed --style swiss --pages 5 --png

# X/Twitter 单图
inkwell card --platform x-twitter --style dark-bold --pages 1 --png

# Pinterest 竖图
inkwell card --platform pinterest --style editorial --pages 1 --png
```

| 风格 | 背景 | 主色 | 字体 |
|------|------|------|------|
| `swiss` Swiss 极简 | `#F5F5F0` | `#D62828` | Inter |
| `editorial` 杂志 | `#0E0D0C` | `#D4A04A` | Noto Serif SC |
| `clean-light` 浅色 | `#FFFFFF` | `#0066CC` | PingFang SC |
| `dark-bold` 深色大胆 | `#1A1A2E` | `#E94560` | Inter |

### 封面设计建议

内置 6 种高转化封面模式：

| 模式 | 适用 |
|------|------|
| 大标题冲击型 | 干货教程、工具推荐 |
| 数据对比型 | 测评、横评、性能对比 |
| 截图证据型 | 工具实操、代码教程 |
| 提问钩子型 | 观点分析、趋势解读 |
| 清单/盘点型 | 合集、Top N、工具箱 |
| 前后对比型 | 优化技巧、改造教程 |

```bash
# 单个推荐
inkwell advise --topic "Docker 镜像优化" --type tutorial

# 多个备选
inkwell advise --topic "10 个好工具" --type list --multi
```

### 设计质量审计

| 门 | 检查内容 |
|----|---------|
| Gate 1 主题与载体合理性 | 有无标题、内容是否完整、有无空 section |
| Gate 2 视觉密度基准 | 字号层级 ≥3、视觉锚点 ≥3、颜色数 ≥2 |
| Gate 3 可编辑交付 | 无 base64 图片、有 charset、无内嵌 script |

### 公众号兼容铁律

| 禁用 | 替代方案 |
|------|---------|
| `display:flex` / `grid` | `<table>` + `<td width>` 均分布局 |
| `display:inline-block` 自制图形 | `●` 字符圆点、`→` 字符箭头 |
| `linear-gradient` 渐变 | 实色背景 |
| `<svg>` 装饰 | CSS border 或字符 |
| `data:image;base64` 内嵌图（发布版） | CDN 外链图片 |

### Agent 集成

安装为 AI Agent 的 Skill：

```bash
# WorkBuddy
cp -r skill/ ~/.workbuddy/skills/inkwell/

# Claude / 其他 Agent（按你的 Agent Skill 目录调整）
cp -r skill/ /path/to/your-agent/skills/inkwell/
```

Agent 内调用示例：
```
用户：帮我写一篇关于 Docker 多阶段构建的推文并排版
Agent：
  1. inkwell generate "Docker 多阶段构建" --style tutorial --search → draft.md
  2. inkwell run draft.md --theme graphite-minimal → output/
  3. inkwell cover --title "..." --png → covers/
  4. inkwell publish output/draft_preview.html --target clipboard
```

### Docker 多阶段构建

| 阶段 | 基础镜像 | 作用 | 产物 |
|------|---------|------|------|
| `builder` | `python:3.13-slim` | 装依赖、生成 venv | `/opt/venv` |
| `runtime` | `python:3.13-slim` | 只拷 venv | 精简运行时镜像 |

优化点：非 root 用户运行、dumb-init 信号转发、无编译工具、层缓存友好。

### 项目结构

```
inkwell/
├── src/inkwell/
│   ├── cli.py                # 13 个子命令入口
│   ├── core.py               # 流水线编排（md → html → 图片 → 校验）
│   ├── processors/
│   │   ├── markdown_proc.py  # Markdown → 内联样式 HTML，15 套主题
│   │   ├── image_proc.py     # 压缩 / CDN 上传 / base64 双轨
│   │   └── validator.py      # 公众号兼容性静态扫描
│   ├── cover_gen.py          # 21:9 + 1:1 杂志封面
│   ├── social_card.py        # 11 个平台社交卡片
│   ├── publisher.py          # 富文本剪贴板 / 微信公众号草稿箱
│   ├── wordcheck.py          # 敏感词与广告法合规检测
│   ├── toc.py                # 目录卡片
│   ├── stats.py              # 字数与阅读时长
│   ├── generator.py          # 5 种风格草稿骨架
│   ├── searcher.py           # 选题素材搜索
│   ├── screenshot.py         # Playwright HTML → PNG
│   ├── design_audit.py       # 三门设计审计
│   └── cover_advisor.py      # 封面设计建议
├── tests/                    # 144 条测试
├── examples/  sample/        # 示例文章
└── skill/                    # Agent Skill 定义
```

### 测试

```bash
pytest tests/ -v --cov=inkwell --cov-report=term-missing
ruff check src/ tests/
ruff format --check src/ tests/
```

提交前建议安装本地钩子，与 CI 门禁保持一致：

```bash
pip install pre-commit && pre-commit install
```

### 参与贡献

| 文档 | 说明 |
|------|------|
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 开发环境、分支约定、公众号兼容铁律 |
| [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) | 社区行为准则 |
| [SECURITY.md](./SECURITY.md) | 漏洞报告渠道与关注的风险面 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更记录 |

发现可复现的缺陷或想提功能请求，请用 [Issue 模板](https://github.com/lijinhongucl-pixel/inkwell/issues/new/choose)；
用法咨询与想法讨论更适合走 Discussions。

---

## English

> **⚠️ The PyPI distribution is `inkwell-press`, not `inkwell`**
>
> - `pip install inkwell` → an unrelated **Qt dark theme** ([pkkid/python-inkwell](https://github.com/pkkid/python-inkwell))
> - `pip install inkwell-cli` → an unrelated **podcast-to-markdown tool** ([chekos/inkwell-cli](https://github.com/chekos/inkwell-cli)). That project also ships an `inkwell` import package and an `inkwell` console command, so **do not install both into the same Python environment**
>
> ✅ This project's distribution name is `inkwell-press` (**not uploaded to PyPI yet** — install from source for now, see [Install](#install))

### The Problem

```
Write article → Format for 30 min → Paste to WeChat → Styles break → Fix →
Paste again → Code blocks messed up → Fix again → Need cover image →
Search stock photos → Not good enough → Open Canva → Export → Upload →
Now adapt for Xiaohongshu → Format again...
```

**The average content creator spends 1+ hour on formatting and visuals per article.**

Inkwell compresses this entire workflow into one command.

```bash
inkwell run article.md              # Format + images + validation
inkwell cover --title "Title" --png  # Magazine cover + PNG
inkwell card --platform xhs --png    # Xiaohongshu cards + PNG
inkwell publish --target clipboard   # Copy to clipboard, paste and publish
```

### How It Compares

| Feature | doocs/md (11.7k stars) | mdnice | xiaohu-wechat-format | **Inkwell** |
|---------|:---:|:---:|:---:|:---:|
| Markdown → WeChat HTML | Web app | Web app | Python CLI | **Python CLI** |
| Magazine cover generator | Docker deploy | No | Gemini API | **Built-in (no AI API needed)** |
| Cover design advisor | No | No | No | **6 high-conversion patterns** |
| Social cards (IG/X/LinkedIn/Pinterest/YT/XHS) | No | No | No | **11 platforms, 4 visual styles** |
| PNG screenshot output | No | No | No | **Playwright 2x Retina** |
| Design quality audit | No | No | No | **3-gate (theme/density/delivery)** |
| Sensitive word / compliance check | No | No | No | **Ad law + platform + general** |
| Auto TOC generation | No | No | No | **H2/H3 extraction + numbering** |
| Word count / reading time | No | No | No | **CN/EN split + structural analysis** |
| Topic search | No | No | No | **GitHub trending + custom backend** |
| Draft skeleton generator | No | No | No | **5 styles + search auto-fill** |
| WeChat draft push | No | No | Yes | **Yes** |
| AI Agent integration | No | No | Claude Code | **Any Agent (universal Skill)** |
| Docker multi-stage | Yes | No | No | **Yes (~120MB)** |

**In one sentence**: They are formatters. Inkwell is a publishing pipeline.

### Install

```bash
# From source (works today)
git clone https://github.com/lijinhongucl-pixel/inkwell.git && cd inkwell
pip install -e .
pip install -e ".[dev]"      # only if you need tests / lint

# Docker
docker build -t inkwell .
```

#### From PyPI (distribution `inkwell-press`, **not published yet**)

```bash
pip install inkwell-press
```

**Why the distribution name differs from the command name.** The plain `inkwell` name on
PyPI is taken by an unrelated Qt theme, so this project's distribution is named
`inkwell-press`. After installing, both the import package and the console command are
still named `inkwell`.

⚠️ **This distribution has not been uploaded to PyPI yet**, so the line above currently
fails with `No matching distribution found`. Use the source install for now.

### Quick Start

```bash
# Full pipeline
inkwell run article.md -o ./output --theme moyu-green

# Search trending topics
inkwell search "AI agent" --limit 10

# Generate draft with auto-search
inkwell generate "Docker optimization" --style tutorial --search

# Magazine cover + PNG
inkwell cover --title "AI" --kicker "2026" -o ./covers/ --png

# Xiaohongshu cards + PNG
inkwell card --platform xhs --style editorial --pages 3 -o ./cards/ --png

# Publish to clipboard or WeChat draft
inkwell publish output/article_preview.html --target clipboard
```

> **Getting CDN image links**: `run` needs all three — the `GITHUB_TOKEN`
> environment variable, `--github-repo owner/repo`, and `--cdn-base <prefix>` — to
> upload images and emit external URLs. If any one is missing, images fall back to
> inline base64 (and the two output files become identical); the CLI tells you what
> is missing.
>
> ```bash
> export GITHUB_TOKEN=ghp_xxx
> inkwell run article.md \
>   --github-repo your-name/your-image-repo \
>   --cdn-base https://cdn.jsdelivr.net/gh/your-name/your-image-repo@main
> ```
>
> ⚠️ An HTML file with inline base64 images should **not** be pasted into the WeChat
> editor directly — the images turn into garbled text. Configure the CDN link above,
> or open the file in a browser and select-all copy.

### Modules

| Module | Description |
|--------|-------------|
| `MarkdownProcessor` | Markdown → WeChat-compatible HTML (15 themes, inline styles) |
| `ImageProcessor` | PIL compression + GitHub Contents API CDN upload, with base64 dual-track fallback |
| `CopyCompatValidator` | Static scan for 6 banned clipboard patterns |
| `ContentSearcher` | GitHub API search + web/custom adapters |
| `DraftGenerator` | 5 article style skeletons with search auto-fill |
| `CoverGenerator` | Magazine cover (21:9 + 1:1, dark editorial style) |
| `SocialCardGenerator` | Social cards (11 platforms: IG/X/LinkedIn/Pinterest/YT/XHS/WeChat, 4 styles) |
| `DesignAuditor` | 3-gate design quality audit |
| `CoverAdvisor` | 6 high-conversion cover pattern advisor |
| `Screenshotter` | Playwright headless PNG capture, degrades gracefully when unavailable |
| `Publisher` | Rich-text (HTML flavor) clipboard + WeChat draft API |
| `WordChecker` | Sensitive word / compliance detection (ad law + platform + general) |
| `TOCGenerator` | Auto table-of-contents card from Markdown headings |
| `ArticleAnalyzer` | Word count, reading time, structural analysis |

Typed: the package ships a `py.typed` marker, so downstream type checkers pick up the inline annotations.

### Testing

```bash
pytest tests/ -v --cov=inkwell --cov-report=term-missing
ruff check src/ tests/
ruff format --check src/ tests/
```

### Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md). All contributions welcome!

For security issues, please follow [SECURITY.md](./SECURITY.md) instead of opening a public issue.
By participating you agree to the [Code of Conduct](./CODE_OF_CONDUCT.md).

### Changelog

See [CHANGELOG.md](./CHANGELOG.md).

### License

[MIT](./LICENSE) — Copyright (c) 2026 Inkwell contributors
