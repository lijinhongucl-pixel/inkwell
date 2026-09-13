# Security Policy

## 支持的版本

只对最新发布版本提供安全修复。

| 版本 | 支持 |
|------|------|
| 最新 release | ✅ |
| 更早版本 | ❌ |

## 报告漏洞

**请不要用公开 Issue 报告安全漏洞。**

请通过 GitHub 的私密渠道报告：

1. 打开仓库的 **Security** 标签页
2. 点击 **Report a vulnerability**
3. 填写复现步骤、影响范围与你的判断依据

我们会尽快确认并回复，修复发布后会在 CHANGELOG 与 Release Notes 中致谢（如果你愿意署名）。

## 本项目关注的威胁面

Inkwell 是一个本地内容处理 CLI，主要风险集中在以下几处，报告时请优先说明是否涉及：

| 区域 | 潜在风险 |
|------|----------|
| `publisher.py` | 微信 `access_token` / `AppSecret` 的处理与日志泄露 |
| `processors/image_proc.py` | `GITHUB_TOKEN` 的使用、CDN 上传路径穿越 |
| `screenshot.py` | 调用 Node 子进程时的参数注入 |
| `searcher.py` | 自定义搜索后端 URL 的 SSRF 风险 |
| 任意位置 | 读取 Markdown / 图片时的路径穿越 |

## 安全使用建议

- 凭证一律通过环境变量传入（`GITHUB_TOKEN` / `WECHAT_APP_ID` / `WECHAT_APP_SECRET`），不要写进配置文件提交
- 不要对来源不明的 Markdown 直接执行 `run` 并开启上传
- 本工具会调用 Node.js（Playwright）渲染截图，请在受信任环境中运行
