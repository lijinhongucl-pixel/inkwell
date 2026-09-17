# Inkwell 架构文档

> 本文档面向 contributors 和 maintainer，描述项目的模块划分、数据流和扩展点。
> 若你只想使用 Inkwell，请看 [README](../README.md)。

## 目录

- [总体架构](#总体架构)
- [模块清单](#模块清单)
- [数据流](#数据流)
- [扩展点](#扩展点)
- [测试策略](#测试策略)
- [依赖关系](#依赖关系)

---

## 总体架构

Inkwell 是一条**线性流水线**（Pipeline），每个处理单元（Processor）只做一件事，输入 str/Path，输出 str/Path。Pipeline 按固定顺序串起来：

```
Markdown 文件
    │
    ▼
MarkdownProcessor    → HTML 骨架（带内联样式 + <span leaf> 包裹）
    │
    ▼
ImageProcessor       → 图片压缩 + 上传 CDN（失败降级 base64）
    │                  生成两版：发布版（外链）+ 本地预览版（base64 内嵌）
    ▼
CopyCompatValidator  → 公众号剪贴板兼容性静态扫描
    │
    ▼
两份 HTML 文件（*.html + *_本地版.html）
```

CLI 层（`cli.py`）只做参数装配和最终输出，不参与数据处理。

---

## 模块清单

| 文件 | 行数 | 职责 |
|------|------|------|
| `core.py` | ~98 | `Pipeline` 编排器、`PipelineConfig`、`PipelineResult` |
| `cli.py` | ~528 | argparse 命令分发，13 个子命令 |
| `processors/markdown_proc.py` | ~407 | Markdown → HTML 转换、主题渲染、span leaf 包裹 |
| `processors/themes.py` | ~150 | 15 套主题色板定义 |
| `processors/image_proc.py` | ~200 | 图片压缩、CDN 上传、双版本生成 |
| `processors/validator.py` | ~75 | 兼容性扫描，返回 `ValidationResult` |
| `publisher.py` | ~518 | 公众号草稿箱推送、图片转存微信图床 |
| `cover_gen.py` | ~358 | 杂志封面生成（21:9 + 1:1） |
| `social_card.py` | ~523 | 11 平台社交卡片生成 |
| `wordcheck.py` | ~328 | 敏感词 / 合规检测 |
| `stats.py` | ~277 | 字数统计、阅读时长分析 |
| `toc.py` | ~80 | 文章目录（TOC 卡片）生成 |
| `generator.py` | ~279 | 草稿骨架生成（5 种风格） |
| `searcher.py` | ~100 | 选题搜索（GitHub trending + 自定义） |
| `design_audit.py` | ~240 | 三门设计审计（主题/密度/交付） |
| `cover_advisor.py` | ~80 | 封面设计建议（6 种高转化模式） |
| `screenshot.py` | ~60 | Playwright PNG 截图 |

---

## 数据流

### `inkwell run`（主流程）

```
PipelineConfig(input_md, output_dir, theme, ...)
    │
    ▼
Pipeline.run()
    │
    ├── 1. MarkdownProcessor.convert(md_text) → html_str
    ├── 2. ImageProcessor.process_html(html, base_dir) → (html, uploads)
    ├── 3. 写发布版 → output_dir/{stem}_预览.html
    ├── 4. ImageProcessor.to_local_preview(html) → local_html
    │      写本地版 → output_dir/{stem}_预览_本地版.html
    └── 5. CopyCompatValidator.scan(preview_path) → ValidationResult
                                                              │
                                                              ▼
                                              PipelineResult(publish_html, local_html,
                                                            uploaded_images, compat_warnings)
```

### `inkwell publish --target wechat`

```
HTML 文件
    │
    ▼
Publisher.publish_to_wechat()
    │
    ├── 1. 扫描 <img src>，逐张调 media/uploadimg 转存到 mmbiz.qpic.cn
    ├── 2. 替换 HTML 中的 src 为微信图床地址
    ├── 3. 封面图 → material/add_material 获取 thumb_media_id
    └── 4. draft/add 建草稿
```

---

## 扩展点

### 新增排版主题

只需改 `src/inkwell/processors/themes.py`：

```python
THEMES["my-new-theme"] = {
    "bg": "#FFFFFF",
    "text": "#1F2937",
    "primary": "#059669",
    "accent": "#A7F3D0",
    "highlight": "#065F46",
    "underline": "#A7F3D0",
    "font": "'PingFang SC', sans-serif",
}
THEME_META.append({"id": "my-new-theme", "name": "我的主题", "desc": "场景描述"})
```

转换逻辑自动复用，不需要改 `markdown_proc.py`。

### 新增社交卡片平台

在 `social_card.py` 的 `PLATFORM_SPECS` 里加一项：

```python
PLATFORM_SPECS["my-platform"] = CardSpec(width=1080, height=1080, ...)
```

### 新增校验规则

在 `validator.py` 的 `FORBIDDEN_PATTERNS` 里加一条正则：

```python
FORBIDDEN_PATTERNS.append(
    ("禁用的特性名", re.compile(r"some-forbidden-pattern", re.I))
)
```

---

## 测试策略

- **197 条测试**，覆盖所有 processor 和 CLI 命令
- 外部依赖（Playwright、微信 API）用 mock server
- CI 矩阵：ubuntu-latest / macos-latest / windows-latest × Python 3.11/3.12/3.13
- 测试文件：`tests/test_*.py`，每个模块独立测试文件

跑测试：

```bash
pytest -v
# 或只跑某一模块
pytest tests/test_pipeline.py -v
```

---

## 依赖关系

```
cli.py
  └─ core.py
       ├─ processors/markdown_proc.py
       │    └─ processors/themes.py
       ├─ processors/image_proc.py
       └─ processors/validator.py
  └─ publisher.py（独立模块）
  └─ cover_gen.py（独立模块）
  └─ social_card.py（独立模块）
  └─ wordcheck.py（独立模块）
  └─ stats.py（独立模块）
  └─ toc.py（独立模块）
  └─ generator.py（独立模块）
  └─ searcher.py（独立模块）
  └─ design_audit.py（独立模块）
  └─ cover_advisor.py（独立模块）
```

所有 publish/cover/card/wordcheck/stats/toc/generator/searcher/audit/advisor 模块相互独立，不互相依赖，只通过 CLI 层组合调用。

---

## 设计原则

1. **线性流水线**：Processor 只做一件事，输入输出明确
2. **双轨产出**：发布版（外链）+ 本地预览版（base64），逐字节可校验一致性
3. **不依赖 AI 生图 API**：封面和卡片走内置模板 + Pillow，离线可用
4. **公众号剪贴板铁律**：禁 flex/grid/inline-block/linear-gradient/base64 图（发布版）
5. **Validator 不输出**：只返回结构化结果，由 CLI 层决定怎么展示

---

_本文档随版本演进，重大架构变更请同步更新。_
