---
name: inkwell
description: 全链路视觉内容工具。Markdown 转公众号 HTML、杂志封面生成、小红书社交卡片、封面设计建议、设计质量审计、选题搜索、草稿自动生成、敏感词检测、字数统计、目录生成。当用户需要写推文、排版文章、做封面、出小红书图、搜索选题、生成草稿、审计设计质量、检查合规时触发。触发词：写推文、排版、公众号文章、做封面、出封面图、小红书图文、社交卡片、内容搜索、选题灵感、生成草稿、Markdown 转换、设计审计、敏感词检测、字数统计、目录生成。
version: 0.7.9
---

# inkwell Skill

从选题到发布全链路覆盖的视觉内容工具。一条命令完成搜索选题→生成草稿→排版文章→做封面→出社交卡片→合规检测→质量审计→发布。

## 十三大命令

| 命令 | 用途 |
|------|------|
| `generate` | 根据主题生成 Markdown 草稿（5 种风格骨架） |
| `search` | 内容搜索（GitHub 热门项目、自定义后端） |
| `run` | Markdown → 公众号 HTML 排版 + 图片处理 + 校验 |
| `cover` | 生成杂志风封面（21:9 主封面 + 1:1 方图） |
| `card` | 生成社交卡片（小红书 3:4 轮播等 11 个平台） |
| `advise` | 封面设计建议（6 种高转化模式智能推荐） |
| `audit` | 三门设计质量审计 |
| `wordcheck` | 敏感词 / 合规检测（广告法极限词 + 平台违规词 + 通用敏感词） |
| `stats` | 字数统计 + 阅读时间 + 结构分析 |
| `toc` | 自动生成文章目录卡片（H2/H3 提取 + 编号） |
| `validate` | 检查 HTML 是否有公众号禁忌写法 |
| `publish` | 发布内容（富文本写入剪贴板 / 公众号草稿箱） |
| `themes` | 列出所有排版主题 |

## 工作流

### 场景一：用户说「帮我写一篇关于 X 的推文并做完」

1. **搜索素材**：`inkwell search "X" --source github --limit 10 --markdown`
2. **生成草稿**：`inkwell generate "X" --style tutorial -o draft.md`
3. **Agent 润色**：基于草稿骨架填充实际内容
4. **排版发布**：`inkwell run draft.md --theme moyu-green -o ./output`
5. **封面建议**：`inkwell advise --topic "X" --type tutorial --multi`
6. **生成封面**：`inkwell cover --title "X" --kicker "..." --data ... -o ./covers/`
7. **质量审计**：`inkwell audit ./covers/cover_01_21x9.html --type cover`

### 场景二：用户说「帮我做一套小红书图文」

1. `inkwell card --platform xhs --style editorial --pages 5 --titles "封面" "要点1" "要点2" "要点3" "总结" -o ./cards/`
2. `inkwell audit ./cards/card_cover_xhs.html --type cover`

### 场景三：用户已有文章想排版

1. `inkwell run article.md --theme graphite-minimal`
2. 产出在 `./output/`，含**两版**：
   - `xxx_预览.html` —— 发布版，图片走 CDN 外链，用于复制到公众号
   - `xxx_预览_本地版.html` —— 图片内嵌 base64，用于 IDE 预览等离线环境
3. `inkwell publish ./output/xxx_预览.html --target clipboard`
   （以富文本写入剪贴板，切到公众号编辑器直接粘贴即为排版效果）

### 场景四：用户想找选题灵感

1. `inkwell search "AI工具" --source github --limit 20 --markdown -o topics.md`

### 场景五：用户写完文章想检查合规

1. `inkwell wordcheck article.md`（扫描敏感词，给出替换建议）
2. `inkwell stats article.md`（查看字数和阅读时间）
3. `inkwell toc article.md -o toc.html`（生成目录卡片）

### 场景六：用户要在文章开头插入目录

1. `inkwell toc article.md --theme moyu-green -o toc.html`
2. 把 toc.html 的 `<table>` 部分粘贴到文章开头

## 主题选择指南

| 题材 | 推荐主题 |
|------|---------|
| 教程、测评、工具盘点 | `moyu-green` 摸鱼绿 |
| 深度分析、观点 | `red-white` 红白色系 |
| 设计、科技评论 | `graphite-minimal` 石墨极简 |
| 禅意、极简生活 | `zen-whitespace` 留白禅意 |
| 工具对比、评测 | `moyu-ticket` 摸鱼票据 |
| 内刊手记、案例复盘 | `olive-journal` 橄榄手记 |
| 深度长文 | `classic-serif` 经典衬线 |
| 科技、AI、编程 | `cyber-neon` 赛博霓虹 |
| 生活、美食、旅行 | `coffee-mocha` 咖啡摩卡 |
| 商务、财经、职场 | `ocean-blue` 海洋蓝 |
| 品牌、生活方式、情感 | `sunset-warm` 日落暖橙 |
| 传统文化、诗词、人文 | `ink-wash` 水墨山水 |
| 环保、自然、健康 | `forest-deep` 森林深绿 |
| 创意、设计、艺术 | `royal-purple` 皇家紫 |
| 时尚、美妆、穿搭 | `sakura-pink` 樱花粉 |

## 封面模式指南

| 文章类型 | 推荐封面模式 |
|---------|------------|
| 教程/指南 | 大标题冲击型 / 截图证据型 / 前后对比型 |
| 测评/横评 | 数据对比型 / 截图证据型 |
| 观点/分析 | 提问钩子型 / 数据对比型 |
| 合集/盘点 | 清单盘点型 / 大标题型 |

## 社交卡片规格

**中文平台**

| 平台 | 比例 | 用途 |
|------|------|------|
| `xhs` 小红书 | 3:4 | 轮播图文（封面+内容页） |
| `wechat-cover` | 21:9 + 1:1 | 公众号封面 |
| `wechat-article` | 16:9 | 公众号正文图 |
| `weibo` 微博 | 1:1 | 社交分享 |

**海外平台**

| 平台 | 比例 | 用途 |
|------|------|------|
| `instagram-feed` IG Feed | 1:1 | 轮播帖子 |
| `instagram-story` IG Story | 9:16 | 限时动态 / Reels 封面 |
| `x-twitter` X | 16:9 | 推文配图 |
| `linkedin` LinkedIn | 1.91:1 | 职场动态 |
| `pinterest` Pinterest | 2:3 | 信息流竖图 |
| `youtube-thumb` YouTube | 16:9 | 视频封面 |

| 视觉风格 | 调性 |
|---------|------|
| `swiss` | Swiss 极简（红蓝对比、可见栅格） |
| `editorial` | 杂志深色（纸色底、衬线字、金色点缀） |
| `clean-light` | 浅色干净（蓝橙点缀、PingFang SC） |
| `dark-bold` | 深色大胆（亮粉色锚点） |

## 设计审计三门

| 门 | 检查 |
|----|------|
| Gate 1 主题合理性 | 有标题、有内容、无空 section |
| Gate 2 视觉密度 | 字号层级 ≥3、锚点 ≥3、颜色 ≥2（封面标准） |
| Gate 3 可编辑交付 | 无 base64、有 charset、无 script |

## 安装

```bash
pip install -e .

# 复制 Skill 到你的 Agent 目录（按实际路径调整）
cp -r skill/ /path/to/your-agent/skills/inkwell/
```
