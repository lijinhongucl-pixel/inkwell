# Inkwell 社区推广文案(4 平台)

> 项目地址:https://github.com/lijinhongucl-pixel/inkwell
> AtomGit 镜像:https://atomgit.com/gcw_TZqg0rJ8/inkwell

---

## 1. V2EX(/share 或 /create 区)

**标题**:分享一个自己写的 CLI,一条命令从 Markdown 干到公众号草稿箱

**正文**:

前阵子实在受不了每次发文的手动流程了。写完 Markdown,排版调半小时,粘到公众号样式崩了再调,找封面图翻素材库,做小红书又排一遍。一次发布花在视觉上的时间超过一小时。

所以写了个 Python CLI 叫 Inkwell,把这整条链路压成一条命令:

```
inkwell run article.md           # 排版 + 图片处理 + 校验
inkwell cover --title "标题"      # 杂志封面
inkwell card --platform xhs       # 小红书社交卡片
inkwell publish --target wechat   # 推到公众号草稿箱
```

和 doocs/md、mdnice 的区别:它们只解决排版一环,后面的封面、卡片、发布都得手动。Inkwell 从排版到推送草稿箱一次跑完,正文图自动转存微信图床。

技术栈是 Python 3.11+,197 条测试,有 Docker 镜像。MIT 协议,自己用也方便改。

不追求 stars,主要是想听技术圈对这个方向的反馈。如果你也在做内容,或者手写过公众号排版脚本,欢迎来看看实现思路:

https://github.com/lijinhongucl-pixel/inkwell

---

## 2. 少数派(Matrix 投稿)

**标题**:一条命令完成公众号排版+封面+发布,这个 CLI 把发文时间从 1 小时压到 3 分钟

**正文**:

作为一个同时运营公众号、小红书、LinkedIn 的人,我最痛苦的不是写,是发。

一篇 3000 字的文章写完后,接下来要做的事:

- 排版进公众号编辑器(样式经常崩)
- 压缩配图,手动上传
- 做封面图(Canva 又要开一次)
- 小红书图文重新排版
- 实际推送

平均花在排版和视觉上的时间超过 1 小时。

后来我用 Python 写了个 CLI 工具叫 **Inkwell**,把这整个流程做成了一条命令链:

```
inkwell run article.md           排版 + 图片处理 + 校验
inkwell cover --title "标题"      杂志封面(PNG)
inkwell card --platform xhs      小红书社交卡片
inkwell publish --target wechat  推送到草稿箱
```

**几个我比较喜欢的细节:**

- 封面内置 6 种高转化模式,不需要 AI 生图 API
- 11 个平台的社交卡片(小红书/Instagram/X/LinkedIn...)
- 正文图自动转存到微信图床(微信会过滤外链图)
- 敏感词检测,发文前自查
- 剪贴板模式:排版完直接粘贴到公众号编辑器

开源,MIT 协议,GitHub 上有详细文档。

**如果你也是一人多平台运营,或者对内容自动化感兴趣:**

https://github.com/lijinhongucl-pixel/inkwell

欢迎提 issue 或 discussion,我比较想知道大家在排版/发布环节最痛的点是什么。

---

## 3. 掘金(技术博文)

**标题**:用 Python 写了一个全链路发布 CLI,197 条测试,从 Markdown 到公众号草稿箱

**正文**:

## 为什么做

市面已有 doocs/md(11.7k stars)、mdnice 等优秀排版工具,但它们都是 Web 编辑器,只解决「Markdown → HTML」这一步。后面还有封面、社交卡片、图片转存、合规检测、推送草稿箱,每一步都得换工具手动跑。

所以做了一个 Python CLI:**Inkwell** —— 把从写完 Markdown 到公众号草稿箱的整条链路压成一条命令。

## 技术设计

整个项目几个关键决策:

### 1. 全链路而非单点
排版只是第一步。真正的痛点在后面:正文图微信不认外链得转存,封面尺寸有规范,不同平台卡片尺寸不同,发文前要查敏感词。每一环都是独立模块,但用 Pipeline 串起来一次跑完。

### 2. 不依赖 AI 生图 API
封面生成走内置模板 + Pillow,不调外部 API。好处是离线可用、无 token 消耗、可预测效果。

### 3. 双轨产出
- 发布版:外链 CDN 图(公众号粘贴时微信自动转存)
- 本地预览版:base64 内嵌(IDE 沙箱也能看效果)
两版逐字节可校验一致性。

### 4. 测试覆盖
197 条测试,CI 三平台矩阵(ubuntu/macos/windows)。涉及外部依赖(Playwright、微信接口)的部分用 mock server 真跑。

## 和同类工具对比

| 能力 | doocs/md | mdnice | Inkwell |
|------|:--:|:--:|:--:|
| 形态 | Web | Web | CLI + Docker |
| 封面 | 无 | 无 | 内置 6 模式 |
| 社交卡片 | 无 | 无 | 11 平台 |
| 草稿箱推送 | 无 | 无 | 自动转存图床 |
| 敏感词 | 无 | 无 | 内置 |
| Agent 集成 | 无 | 无 | Skill 协议 |

## 用法

```bash
# 一把跑完整链路
inkwell run article.md
inkwell cover --title "标题" --png
inkwell card --platform xhs --png
inkwell publish --target wechat

# 或者单步
inkwell validate article.html    # 校验公众号兼容性
inkwell layout article.md --theme editorial
```

项目地址:https://github.com/lijinhongucl-pixel/inkwell

MIT 协议,欢迎来提 issue。

---

## 4. 即刻(「我做了个工具」圈子)

**标题**:做了一个 CLI,专门拯救每次发文要花一小时排版的人

**正文**:

包括我在内的很多人,写完文章才是痛苦开始:

排版 → 找封面 → 做卡片 → 转图片格式 → 粘公众号 → 发小红书 → 又排一遍

所以我做了 Inkwell,一条命令从 Markdown 干到公众号草稿箱。

排版 + 封面 + 11 个平台的社交卡片 + 敏感词检测 + 草稿箱推送,一次跑完。

不依赖 AI 生图 API,封面用内置模板生成。开源,Python 写的。

如果你是一人多平台运营,或者也被排版折磨过,来看看:

https://github.com/lijinhongucl-pixel/inkwell

---

## 发布节奏建议

| 时间 | 平台 | 动作 |
|------|------|------|
| Day 1 | V2EX + 即刻 | 先发这两个,开发者氛围浓,反馈快 |
| Day 2-3 | 少数派 + 小红书 | 等首批反馈后优化文案,再出圈 |
| Day 4-7 | 掘金 | 写技术博文沉淀,长尾 SEO |
| 持续 | 知乎 | 找「公众号排版工具」「自动化发文」类问题,回答带项目 |

## 注意事项

- V2EX 语气最克制,千万别营销腔,「不追求 stars 想听反馈」是真实态度
- 少数派读者在意实际效果,截图和 GIF 比文字有用十倍
- 即刻可以更口语化
- 掘金技术读者看重实现细节,对比表和测试数据是加分项
- **所有平台发布前先放 2-3 张实际效果图**,没图的帖子流量差 3 倍
