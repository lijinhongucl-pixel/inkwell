# Inkwell 内容发布流水线

一次内容发布，平均花在排版和视觉上的时间超过 1 小时。Inkwell 用一条命令把这件事压缩到 30 秒以内。

## 为什么需要 Inkwell

市面已有优秀的排版工具，但它们都只解决「排版」这一个环节。**Inkwell 覆盖的是全链路**，从 Markdown 草稿到公众号 HTML，从封面图到社交卡片，一条命令搞定。

核心能力包括：

- Markdown 转公众号兼容 HTML（15 套主题）
- 杂志风封面自动生成（21:9 + 1:1）
- 小红书 / Instagram 等 11 个平台社交卡片
- 敏感词 / 广告法合规检测
- 文章目录 TOC 自动生成

## 性能对比

| 指标 | 手动排版 | Inkwell |
|------|----------|---------|
| 耗时 | 60-90 分钟 | 30 秒 |
| 主题切换 | 手动改 CSS | 一行参数 |
| 合规检查 | 人工审读 | 自动扫描 |
| 多平台适配 | 逐个重做 | 一键生成 |

> 传统排版工具只管「排」，Inkwell 管「排 + 审 + 封 + 卡」全链路。

## 快速上手

安装后三行命令即可完成一次完整发布：

```bash
inkwell run article.md --theme classic-serif
inkwell cover --title "标题" --kicker "AI 工具"
inkwell card --platform xhs --style editorial --pages 5
```

## 总结

如果你也在做内容发布，试试 Inkwell，把时间留给写作本身。

---

以上。
