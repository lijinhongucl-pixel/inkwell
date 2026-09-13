# Contributing to inkwell

感谢你有兴趣为 inkwell 贡献代码！这个项目欢迎各种形式的贡献。

## 快速开始

```bash
# 克隆仓库
git clone <your-fork-url>
cd inkwell

# 创建虚拟环境并安装开发依赖
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 运行测试确认环境正常
pytest tests/ -v
```

## 贡献方式

### 报告 Bug

1. 在 [Issues](../../issues) 页面搜索是否已有相同问题
2. 如果没有，点击 **New Issue** 选择 **Bug Report** 模板
3. 填写环境信息、复现步骤、预期行为和实际行为

### 提交功能建议

1. 在 [Issues](../../issues) 页面搜索是否已有类似建议
2. 点击 **New Issue** 选择 **Feature Request** 模板
3. 描述使用场景、期望行为、替代方案

### 提交代码

1. **Fork** 本仓库
2. 从 `main` 创建特性分支：`git checkout -b feat/your-feature`
3. 编写代码，确保：
   - 新功能有对应测试
   - 所有测试通过：`pytest tests/ -v`
   - 没有个人信息或内部地址泄露
4. 提交 commit，遵循 [Conventional Commits](https://www.conventionalcommits.org/)：
   ```
   feat: add new theme 'cyber-punk'
   fix: handle empty markdown input gracefully
   docs: update README with new flag
   test: add edge case for image compression
   refactor: extract color parsing logic
   ```
5. 推送分支并发起 **Pull Request**

### Pull Request 检查清单

- [ ] 代码通过所有现有测试
- [ ] 新功能有对应的新测试
- [ ] 没有引入个人信息或内部地址
- [ ] 文件读写都显式带上了 `encoding="utf-8"`（见「跨平台铁律」）
- [ ] 验证平台专属分支时 mock 了能力探测（`shutil.which` 等），而不是依赖当前平台
- [ ] 如果新增了 CLI 子命令，更新了 `skill/SKILL.md`
- [ ] 如果新增了主题或视觉风格，更新了 `README.md` 对应表格
- [ ] commit message 遵循 Conventional Commits

## 开发约定

### 分支命名

| 类型 | 前缀 | 示例 |
|------|------|------|
| 新功能 | `feat/` | `feat/png-screenshot` |
| 修复 | `fix/` | `fix/search-chinese` |
| 文档 | `docs/` | `docs/readme-v0.4` |
| 重构 | `refactor/` | `refactor/pipeline-core` |

### 测试

```bash
# 运行全部测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=inkwell --cov-report=term-missing

# 只运行某个模块的测试
pytest tests/test_visual_modules.py -v
```

### 公众号兼容性铁律

贡献排版相关代码时，必须遵守公众号剪贴板的兼容性规则：

| 禁用 | 替代 |
|------|------|
| `display:flex` / `grid` | `<table>` + `<td width>` |
| `display:inline-block` 自制图形 | 字符（`●` `→`） |
| `linear-gradient` | 实色背景 |
| `<svg>` 装饰 | CSS border 或字符 |
| `data:image;base64`（发布版） | CDN 外链 |

新增的主题或排版逻辑必须通过 `CopyCompatValidator` 的校验。

### 跨平台铁律（Windows CI 会抓到）

CI 在 ubuntu / macOS / Windows 三平台都跑测试，下面两条是本项目已经踩过的坑：

1. **所有文件读写必须显式指定 `encoding="utf-8"`**

   ```python
   path.read_text()                        # ✗ Windows 默认 cp1252，含中文直接 UnicodeDecodeError
   path.read_text(encoding="utf-8")        # ✓
   ```

   本项目产出全是中文内容，漏写编码在 macOS / Linux 上**永远发现不了**，只会在 Windows 崩。
   CI 有一道专门的守卫会拦住它：

   ```bash
   ruff check --preview --select PLW1514 src/ tests/
   ```

2. **验证平台专属分支时，要 mock 掉能力探测，而不是依赖当前平台**

   ```python
   # ✗ 只 mock subprocess.run：在非 macOS 上会因 shutil.which("osascript") 返回 None 而抛错
   monkeypatch.setattr("subprocess.run", fake_run)

   # ✓ 同时 mock 能力探测，用例才与运行平台无关
   monkeypatch.setattr("subprocess.run", fake_run)
   monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/osascript")
   ```

### 平台支持现状

真正存在平台差异的只有剪贴板富文本写入这一处：

| 能力 | macOS | Linux | Windows |
|------|-------|-------|---------|
| 排版 / 封面 / 社交卡片 / 兼容性校验 / 字数统计 | ✅ | ✅ | ✅ |
| 剪贴板**富文本**写入（`publish --target clipboard`） | ✅ AppleScript | ✅ 需装 `xclip` | ❌ 降级纯文本 |
| HTML → PNG 栅格化（`--png`） | 需 Node + playwright-core | 同左 | 同左 |

`--png` **不是平台差异**：三个平台都要求自行装 Node.js + `playwright-core`，
缺失时统一降级（输出 HTML、跳过 PNG、给出安装指引），不区分操作系统。

Windows 的富文本剪贴板（CF_HTML）尚未实现，欢迎 PR。

### 新增主题

在 `src/inkwell/processors/markdown_proc.py` 的 `THEMES` 中追加色板：

```python
THEMES["your-theme"] = {
    "bg":        "#FFFFFF",   # 页面底色
    "text":      "#333333",   # 正文色
    "primary":   "#0066CC",   # 主色（标题、列表点、链接）
    "accent":    "#FF6600",   # 点缀色（分割线、装饰）
    "highlight": "#CC0000",   # 斜体高亮
    "underline": "#FFCC00",   # ==高亮== 下划线
    "font":      "Georgia, serif",
}
```

同时在 `THEME_META` 列表登记（否则 `inkwell themes` 不会列出）：

```python
{"id": "your-theme", "name": "主题中文名", "desc": "适用题材"},
```

深色主题会被 `_is_dark_bg()` 自动识别，引用块 / 表格 / 行内代码底色会自适应，
**不要**在主题字典里硬编码这些辅助底色。最后在 `README.md` 主题表格中登记一行。

## 行为准则

参与本项目即代表你同意遵守 [Code of Conduct](./CODE_OF_CONDUCT.md)。请保持友善和尊重。

## License

提交的贡献代码将在 [MIT License](./LICENSE) 下发布。
