# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.9] - 2026-09-13

**修复 CLI 路径下 CDN 图片外链完全失效。** 起因是换陌生用户视角做验收：全新克隆、
干净虚拟环境安装、逐条真跑 README 命令。结果发现 `run` 即使配好有效
`GITHUB_TOKEN`，依然 100% 把图片降级成内嵌 base64。

### Fixed
- **CLI 漏传 CDN 配置，`run` 永远降级 base64**：`cli.py` 构造 `PipelineConfig` 时
  只传了 `github_token`，`github_repo` 与 `cdn_base` 保持空字符串，而 `image_proc`
  的上传判定是 `if token and repo` —— 判定恒为假。后果是发布版 `_预览.html` 里全
  是 base64，且与 `_预览_本地版.html` **字节完全相同**，README 承诺的「发布版走
  CDN 外链」在 CLI 路径下根本不成立
- **`run` 新增 `--github-repo` 与 `--cdn-base`**：分别可用环境变量
  `INKWELL_GITHUB_REPO` / `INKWELL_CDN_BASE` 兜底（Docker 场景无需改命令）
- **配置不全时不再产出畸形外链**：`_upload` 用 `f"{cdn_base}/{path}"` 拼返回地址，
  若只给 `github_repo` 而漏 `cdn_base`，会得到 `/pic.jpg` 这种畸形相对地址，粘进
  公众号后图片全裂。现改为三项（token / repo / cdn_base）必须齐备才走上传，否则
  降级 base64 并明确告警
- **降级时给出可执行的启用指引**：`run` 输出含 base64 时，提示需要同时提供哪三项
  配置才能改用 CDN 外链

### Tests
- 新增 `tests/test_cli.py`：锁死「CLI 参数 → `PipelineConfig`」这段装配。此前 CLI
  层零测试覆盖，`build_parser` / `cmd_run` 从未被测试碰过，缺陷恰好藏在「层与层
  之间的缝」里
- `test_io_modules.py` 补 `TestCdnConfigGuard`：缺 `cdn_base` 或缺 `repo` 时必须
  降级，且不得尝试上传

### Verified
- 真实端到端：对带图文章配齐三项跑 `run`，发布版输出真实 CDN URL（2 张），
  本地版保留 base64（2 张），两版不再相同；上传的文件经 jsDelivr 请求返回
  HTTP 200 且字节数与本地一致

## [0.7.8] - 2026-09-13

**PyPI 发行名改为 `inkwell-press`。** 起因是准备对外介绍文案时去核对包名，
结果发现 README 里的 `pip install inkwell` 装的根本不是本项目。

### Fixed
- **`pip install inkwell` 指向的是别人的包**：PyPI 上的 `inkwell` 是 Michael Shepanski
  的 Qt 深色主题（[pkkid/python-inkwell](https://github.com/pkkid/python-inkwell)，
  最后发布 2023-03），与本项目毫无关系。照 README 安装的人会拿到一个主题库，
  再发现 `inkwell` 命令不存在。发行名改为 `inkwell-press`（已核实该名在 PyPI 上
  未被占用）
- **近名项目 `inkwell-cli` 也必须避开**：PyPI 上的 `inkwell-cli` 是
  [chekos/inkwell-cli](https://github.com/chekos/inkwell-cli)（播客转 Markdown 笔记），
  它的**导入包名与命令名同样叫 `inkwell`**，与本项目在发行名、导入名、命令名三个
  维度全部撞名。README 中英文顶部各加了一段醒目提示，并写明两者不可装进同一环境
- **CHANGELOG 版本顺序颠倒**：0.7.7 被排在 0.7.6 之后，不符合「新版本在前」，
  一并纠正

### Changed
- **README 补上发行名说明**：解释发行名 `inkwell-press` 与命令名 `inkwell` 为何
  不一致；`git clone` 后面的占位地址换成本仓库真实地址
- **导入包名与 CLI 命令名保持不变**（仍是 `inkwell`）：改名只发生在 PyPI 发行层，
  源码、测试、CI 与用户已熟悉的命令都不受影响
- **安装指引改为以源码安装为主**：`inkwell-press` 这个发行包**还没有上传到 PyPI**
  （实测 `/pypi/inkwell-press/json` 返回 404），所以不能只把安装命令换个名字就完事
  —— 那只是把「装错包」变成「装不上」。README 中英文的安装段改为先给可用的源码
  安装，PyPI 单独成节并明确标注尚未发布

## [0.7.7] - 2026-09-13

仓库运维：启用真实 CI 徽章，并把 dependabot 首次运行产生的噪音收干净。

### Changed
- **README 的 CI 徽章换回动态徽章**：占位期用的是不依赖仓库地址的静态徽章
  （只说明「CI 跑在 GitHub Actions 上」，不表达通过与否）。仓库创建、CI 首次全绿
  之后，换成读 `ci.yml` 在 `main` 上最近一次运行结果的动态徽章
- **开发工具链下限对齐到真正验证过的版本**：`ruff>=0.4` → `>=0.16.7`、
  `pytest>=7.4` → `>=9.1.1`、`pytest-cov>=4.1` → `>=7.1.0`、`build>=1.2` → `>=1.6.1`、
  `setuptools>=68.0` → `>=84.0.0`。原先的下限过旧，会让人以为项目支持这些老版本，
  而 CI 因下限宽松，装的其实一直是最新版 —— **声明与实际不一致**。下限应当等于
  验证过的版本；要扩大兼容面，正确做法是先扩 CI 矩阵去测，而不是把下限写低。
  `[dev]` extra 顺带补上 `build`，使 requirements-dev.txt 里「与 `[dev]` 保持一致」
  这句话真正成立
- **CI 里的 GitHub Actions 升到当前主版本**：`checkout` v4→v7、`setup-python`
  v5→v7、`setup-buildx-action` v3→v4、`build-push-action` v5→v7、`codecov-action`
  v4→v7。其中 codecov-action 自 v6 起切到 node24，且 v7 无必填输入（公开仓库
  可无 token 上传），与本项目现有配置兼容
- **运行时依赖 `Pillow` 下限 10.0 → 12.3.0**：源码只用到
  `Image.open` / `resize` / `Image.LANCZOS`，API 面很稳；但 `Pillow>=10.0` 这个
  下限从未被验证过 —— CI 与本地实际装的都是解析出的最新版，10.x 一次都没跑过。
  另外 Pillow 历史上有多次 CVE，下限停在 2023 年的 10.0 会让用户装到已修复
  漏洞的版本。同上，下限应当等于真正验证过的版本

### Fixed
- **CI 不再在 main 上取消进行中的运行**：原先 `cancel-in-progress: true` 对
  `main` 也生效，于是连续两次 push 会把前一次运行取消（`concluded=cancelled`）。
  而 GitHub 的 workflow 徽章把 **cancelled 也算作 failing** —— 结果是代码一次
  都没失败，README 顶部的 CI 徽章却瞬间变成红色的「CI failing」。改为只在
  `pull_request` 上取消，main 的推送排队等待，代价是晚几十秒，换来徽章始终如实
- **dependabot 配置改为按生态整组更新**：原先只对 minor/patch 分组，于是每个
  过期的下限各开一个 PR —— 首次启用一周就攒了 11 个，且全部为红，反而淹没真正的
  信号。改为 major/minor/patch 全部并入同一组，每个生态每周最多 1 个 PR
- **Docker 基础镜像的 Python 主版本不再自动升**：CI 矩阵只测 3.11 / 3.12 / 3.13，
  classifiers 也只声明到 3.13。自动跳到 3.14 等于往发布镜像里塞一个从没被测过的
  解释器，所以加了 `ignore` 规则；要升主版本，应当先扩 CI 矩阵

## [0.7.6] - 2026-09-13

首次推送后 CI 抓出的问题修复。这一轮的价值几乎全在 CI 上：三平台里只有 macOS 全绿，
ubuntu 与 Windows 双双失败，暴露出两个**在 macOS 本地永远跑不出来**的缺陷。

### Fixed
- **非 macOS 平台必挂的测试**：`test_macos_writer_sets_html_flavor` 只 mock 了
  `subprocess.run`，**漏 mock `shutil.which`**。该用例验证的是 AppleScript 命令构造，
  与运行平台无关，但没屏蔽能力探测，于是在 Linux / Windows 上直接
  `RuntimeError: 未找到 osascript`。补上 mock
- **Windows 上 9 个测试 `UnicodeDecodeError`**：测试读取产出 HTML 时写成
  `read_text()`，而 Windows 默认编码是 cp1252，读到 UTF-8 中文就崩
  （`'charmap' codec can't decode byte 0x90`）。测试侧共 14 处文件读写补上
  `encoding="utf-8"`。**库代码本身没有问题** —— `src/inkwell/` 内所有读写此前
  就已显式指定编码，这一轮逐个核对过

### Added
- **编码守卫（CI）**：新增 `ruff check --preview --select PLW1514` 独立步骤，
  机械拦截「文件读写漏写 `encoding`」这一类缺陷。之所以单独一条而不并进主 lint，
  是因为该规则仍在 preview 阶段，全局打开 preview 会让 lint 结果随 ruff 版本漂移
- **CONTRIBUTING 新增「跨平台铁律」与「平台支持现状」**：写明必须显式指定编码、
  验证平台专属分支时要 mock 能力探测，并如实列出三平台能力矩阵

### Changed
- **README 补充平台支持说明**：「复制到公众号」是头号卖点，但富文本剪贴板只在
  macOS（AppleScript）与 Linux（`xclip`）上有实现，**Windows 会降级为纯文本**。
  此前 README 对此只字未提，Windows 用户会白踩一次坑。现在明确写出降级行为与
  替代做法（用浏览器打开 `_预览.html` 手动复制）

## [0.7.5] - 2026-09-13

README 修复、仓库瘦身与仓库地址落位。这一轮解决的是「打开仓库首页就看到裂图」、
「源码树里躺着一堆不该提交的中间产物」、「文档里的链接全指向不存在的占位账号」
三类问题。

### Fixed
- **README 首屏裂图**：CI 徽章用的是 GitHub Actions 动态徽章，仓库尚未 push 时
  该地址必然 404，README 顶部就是一个「图片加载失败」的破框；改为不依赖仓库地址的
  shields.io 静态徽章（`CI` + GitHub Actions 图标），并附注释写明 push 后换回
  真实 CI 状态徽章的替换行

### Changed
- **仓库地址落位**：`pyproject.toml` 的 `[project.urls]`（5 条）、README 的 Issue
  模板链接、`.github/ISSUE_TEMPLATE/config.yml` 的 Discussions 与安全公告链接，
  全部从占位账号 `your-org` 换成真实仓库 `github.com/lijinhongucl-pixel/inkwell`。
  占位期间这些链接一律 404，装到本地的人点进去也是死链

### Removed
- `src/inkwell.egg-info/`：`pip install -e .` 生成的构建产物，内含已过期的
  元数据（旧版本号、`your-org` 链接），被 `.gitignore` 覆盖但一直留在工作区
- `src/processors/`、`src/templates/`：改名前的空壳目录（真正的代码在
  `src/inkwell/processors/`），空目录在 git 里不会提交，但会误导按图索骥的读者
- `output/`：本地跑流水线留下的中间产物与预览文件，可由 `inkwell run` 随时重建
- `.pytest_cache/`、`.ruff_cache/`、各 `__pycache__/`：本地缓存

## [0.7.4] - 2026-09-13

开源仓库规范化。这一轮对着 GitHub 的社区标准清单逐项体检，修掉了**会让 CI 门禁形同虚设、
让装包变重、让品牌名前后不一**的问题，并补齐社区标准文件。

### Fixed
- **CI 覆盖率指向不存在的包（失效）**：`--cov=content_pipeline` 用的还是改名前的旧包名，
  覆盖率采集实际是空的；改为 `--cov=inkwell`
- **CI lint 门禁被绕过**：`ruff check ... || true` 让 lint 永远不失败，
  等于没有门禁；去掉 `|| true`，并补上 `ruff format --check`
- **CI 矩阵缺 3.13**：本地跑的是 3.13，CI 只测 3.11/3.12；补上 3.13 并新增
  macOS / Windows 各一条冒烟任务
- **打包声明了 5 个零引用依赖**：`markdown` / `beautifulsoup4` / `lxml` /
  `requests` / `pygments` 在源码里一次都没用到（AST 全量扫描确认），
  仅 `Pillow` 是真实依赖，从 PyPI 安装时的依赖树显著变小
- **`package-data` 指向不存在的目录**：`templates/*.html`、`templates/*.css`
  在包里根本不存在，是死配置；改为只声明真实存在的 `screenshot.js` 与 `py.typed`
- **`Typing :: Typed` 分类器是空头承诺**：声明了类型化却没有 `py.typed` 标记文件，
  下游类型检查器看不到注解；补上 `py.typed` 并在 CI 中校验它真的被打进 wheel
- **品牌名残留**：`LICENSE` 署名、CI 的 Docker tag、`bug_report.md` 的命令与版本示例、
  `CONTRIBUTING.md` 的覆盖率参数与源码路径，仍写着 `content-pipeline` 旧名
- **Dockerfile 注释与事实不符**：写着「装 build-base 等编译工具」，实际并没有装；
  基础镜像从 3.12 对齐到 3.13，并移除运行时冗余的源码拷贝
- **docker-compose 挂载 `.env` 会在文件不存在时创建目录**：改为通过环境变量或
  `--env-file` 传入

### Added
- `SECURITY.md`：漏洞报告渠道与风险面清单（凭证处理、路径穿越、子进程调用、SSRF）
- `.github/dependabot.yml`：pip / GitHub Actions / Docker 三条更新流水线
- `.github/FUNDING.yml`：惰性占位，需要赞助入口时取消注释即可
- `.github/ISSUE_TEMPLATE/config.yml`：关闭空白 Issue，引导到 Discussions 与私密安全渠道
- `.editorconfig`、`.gitattributes`：统一缩进与换行符（Windows CI 依赖 LF）
- `.pre-commit-config.yaml`：本地钩子与 CI 门禁保持一致
- `requirements-dev.txt`：CI 与本地共用的工具链版本
- `py.typed`：让类型注解对下游生效
- CI 新增 `package` 任务：构建 wheel → 干净虚拟环境安装 → 校验必需资源已打包
- README 补「项目结构」「参与贡献」章节；英文区模块表补充双轨与降级说明

### Changed
- 全仓库用 `ruff format` 统一格式化（24 个文件）
- `input/` 补 `.gitkeep`，使空目录可被 git 跟踪

### Notes
- 测试总数 139 → 144（新增主题注册表一致性与打包资源回归测试）

## [0.7.3] - 2026-09-13

发布链路可用性修复。这一轮把「Markdown → 公众号」主链路上几个**看起来能用、
实际会毁掉结果**的缺陷修掉了，并给此前零测试覆盖的图片处理与发布模块补上回归测试。

### Fixed
- **剪贴板只写纯文本（致命）**：`publish --target clipboard` 之前只往剪贴板写
  纯文本 flavor，粘进公众号得到的是 HTML 源码字面量而不是排版效果。
  现在 macOS 走 AppleScript 写入 `«class HTML»` + 纯文本双 flavor，
  Linux 走 `xclip -t text/html`，其他平台降级纯文本并明确提示改用手动复制
- **本地预览版是空壳**：`ImageProcessor.to_local_preview()` 此前直接返回原文，
  `_预览_本地版.html` 与发布版逐字节相同，CDN 外链不会转 base64，
  IDE 预览面板依旧是裂图。现在记录 CDN→base64 映射并整段替换
  `src="cdn"` → `src="data:..."`（不做前缀拼接，避免残留 URL 前缀把图搞裂）
- **图片上传失败中断流水线**：CDN 上传抛异常会让整个 `run` 崩溃，
  现在降级为内嵌 base64 并记录警告，HTML 照常产出
- **正文提取会截断**：`_extract_section` 用非贪婪正则，正文里嵌套
  `<section>`（目录卡片、图片卡片）时会在第一个 `</section>` 处截断，
  改为标签深度配对提取
- **微信草稿必被拒**：`thumb_media_id` 兜底成 `"default_thumb"` 会被微信
  以 errcode 40007 拒绝，改为缺少时提前明确报错，并透出 errcode/errmsg
- **草稿占位符漏进正文**：`generate` 产出的裸 `TODO:` 行会被渲染成可见文字，
  改为 HTML 注释形式，并让排版器整段剥离 HTML 注释（代码块内的注释保留）
- **审计结论自相矛盾**：`audit` 存在 WARN 时仍输出「所有门通过」，
  现在区分「全部通过 / 有警告 / 未通过」三种结论

### Added
- `tests/test_io_modules.py`：27 条测试覆盖 `image_proc` 与 `publisher`
  （压缩、缩放、alpha 转 RGB、CDN 上传、失败降级、双轨替换、
  嵌套 section 提取、纯文本化、剪贴板 HTML 写入、微信参数校验）
- `test_pipeline.py` 新增 `TestHtmlCommentStripping`（5 条）与
  `TestDraftGeneratorPlaceholders`（2 条）回归测试
- `PipelineResult.image_warnings` 字段，`run` 命令会打印图片处理警告

### Notes
- 测试总数 105 → 139

## [0.7.2] - 2026-09-13

### Fixed

- **封面/卡片内容堆在顶部、下方大片空白（版式头重脚轻）**
  - 21:9 封面、1:1 方图、3:4 社交卡片此前都用普通块级流式布局，
    内容只占画布上部的 25%~40%，下方整片空白，看起来像没做完
  - 修复：全部改为三段式 `<table height:100%>` 布局
    （顶部刊头 / 中部主体 `vertical-align:middle` 撑满剩余空间 / 底部署名），
    内容在画布中垂直居中，构图从「堆在顶部」变为均衡的编辑式版式
  - 卡片新增背景期号水印（`opacity:0.05~0.06`，尺寸为画布长边的 55%），
    填补留白并增加层次

- **封面数据条配色硬编码**
  - `_render_data_bar()` 此前写死 `#d4a04a` / `#ece2cf`，自定义封面配色时不跟随
  - 修复：改为接收 `accent` / `ink` 参数，跟随 `CoverSpec` 配色

- **数据条数字与标签被整体压暗**
  - 数据条容器上挂了 `opacity:0.4`，把分隔线连同数字、标签一起调暗，
    标签几乎不可读
  - 修复：去掉容器 opacity，改用半透明边框色 `{ink}55`，标签透明度提到 0.72

- **PNG 截图失败时抛 Node.js 原始堆栈**
  - 缺少 `playwright-core` 或 Chromium 版本不匹配时，直接抛出
    `MODULE_NOT_FOUND` / `Executable doesn't exist` 的 Node 堆栈，
    且整个命令失败（HTML 明明已经生成成功）
  - 修复：新增 `ScreenshotError` 异常与 `Screenshotter.check_ready()` 预检，
    错误信息带可执行的安装指引；封面/卡片生成器捕获该异常后
    **保留 HTML 输出、跳过 PNG 并打印提示**，不再中断流程

### Added

- `PLAYWRIGHT_CHROMIUM_PATH` 环境变量：指定自定义 Chromium 可执行文件，
  便于使用系统已有浏览器或非标准安装路径
- `Screenshotter.is_available()`：静态方法，判断截图链路是否就绪
- 10 条回归测试：三段式布局、水印、数据条配色、容器 opacity、截图降级

## [0.7.1] - 2026-09-12

### Fixed

- **致命 bug：引号替换破坏全部 HTML 属性**
  - `_inline()` 方法末尾的 `text.replace('"', '「')` 在生成 HTML 标签之后执行，
    把所有 `style="..."` 中的双引号替换成了 `「`，导致 HTML 属性崩溃
  - 典型症状：`<strong style=「color:#52525B;font-weight:bold;「>` 渲染时样式全部失效
  - 修复：将引号替换移到 HTML 标签生成之前，并改为成对替换（`"..."` → `「...」`）

### Added

- **card 命令新增 `--subtitles` / `--bodies` 参数**：
  - 之前只支持 `--titles`，导致社交卡片副标题和正文为空白
  - 现在每页可独立指定标题、副标题、正文
- **更丰富的示例文档** `sample/demo-article.md`：覆盖标题、粗体、列表、表格、引用、代码块全场景

## [0.7.0] - 2026-09-12

### Added

- **6 个海外社交平台**（5→11 平台）：
  - `instagram-feed` IG Feed（1:1, 1080×1080，最多 10 页轮播）
  - `instagram-story` IG Story / Reels（9:16, 1080×1920）
  - `x-twitter` X/Twitter（16:9, 1600×900）
  - `linkedin` LinkedIn（1.91:1, 1200×627）
  - `pinterest` Pinterest（2:3, 1000×1500）
  - `youtube-thumb` YouTube Thumbnail（16:9, 1280×720）
- **卡片模板参数化重构**：从硬编码 3:4 小红书竖图改为通用 `aspect-ratio` 参数化，自适应所有比例
- **海外平台自动英文**：`region: "global"` 的平台自动切换 `lang="en"`、占位文字改为英文
- **自适应字号**：根据平台高度等比缩放标题/正文/标签字号
- **8 个新测试**覆盖全部海外平台（总数 83→91）

### Changed

- `XHS_COVER_TEMPLATE` / `XHS_CONTENT_TEMPLATE` 重命名为 `CARD_COVER_TEMPLATE` / `CARD_CONTENT_TEMPLATE`
- `PLATFORM_SPECS` 每个平台新增 `region` 字段（`cn` / `global`）
- `SocialCardGenerator.generate()` 新增 `_parse_ratio` 方法处理复合比例

## [0.6.0] - 2026-09-12

### Added

- **`WordChecker` 敏感词检测模块**：内置三类敏感词库（广告法极限词 40+ 条、平台高频违规词 30+ 条、通用敏感词 30+ 条），自动跳过代码块，输出风险等级和替换建议
- **`TOCGenerator` 文章目录生成模块**：自动提取 Markdown H2/H3 标题，自动编号（1 / 1.1 / 1.2），渲染公众号兼容的目录卡片 HTML
- **`ArticleAnalyzer` 字数统计模块**：中英文分开计数、代码块排除、结构分析（段落数/标题数/代码块数/表格数/图片数/链接数）、阅读时长（中文 300 字/分钟 + 英文 200 词/分钟）+ 朗读时长
- **3 个新 CLI 子命令**：`wordcheck`、`stats`、`toc`（均支持 `--json` 输出）
- **31 个新测试**覆盖三个新模块（总数 52→83）

## [0.5.0] - 2026-09-12

### Added

- **8 套新排版主题**（7→15）：赛博霓虹 `cyber-neon`、咖啡摩卡 `coffee-mocha`、海洋蓝 `ocean-blue`、日落暖橙 `sunset-warm`、水墨山水 `ink-wash`、森林深绿 `forest-deep`、皇家紫 `royal-purple`、樱花粉 `sakura-pink`
- **暗色主题自适应**：自动检测背景亮度，暗色主题（如 cyber-neon）的引用块、代码块、表格行底色自动切换为暗色
- 6 个新测试覆盖全部新主题（总数 46→52）

### Changed

- **项目更名为 Inkwell**（前身 content-pipeline），新的品牌名称和 CLI 入口
- 全新 README：双语版、badges、竞品对比表、before/after 场景叙事
- 脱敏审计：移除所有内部 Skill 名引用、硬编码本机路径、第三方项目名引用

### Fixed

- 修复 screenshot.py 硬编码本机 Node.js 路径，改为自动检测 + 环境变量 `PLAYWRIGHT_NODE_PATH` + npm global root 三级降级
- 修复 pyproject.toml build-backend 引用错误

## [0.4.0] - 2026-09-11

### Added

- **Playwright PNG 截图**：`cover --png` 和 `card --png` 标志，自动调用 Chromium 无头截图，Retina 2x 高清输出
- **`publish` 子命令**：支持 `--target clipboard`（剪贴板复制正文）和 `--target wechat`（公众号草稿箱 API 推送）
- **草稿生成器接搜索自动填充**：`generate --search` 标志，自动搜索参考素材填充骨架
- **封面背景三层纹理增强**：radial-gradient 暗角聚焦 + SVG feTurbulence 噪点纸纹 + linear-gradient 墨色洗影
- **`Screenshotter` 模块**：Python subprocess 调 Node.js Playwright 脚本，支持 5 种尺寸
- **`Publisher` 模块**：`PublishResult` 数据类，双模式发布
- **中文主题搜索降级**：GitHub 搜索中文返回空时自动提取关键词映射为英文重试

### Changed

- `CoverGenerator` 支持 `png` 参数，不依赖时零副作用
- `SocialCardGenerator` 同上
- `DraftGenerator.generate_with_search()` 新增，保留原 `generate()` 不变

### Fixed

- 修复 `advise_multi` 在 `general` 类型下候选不足 `top_n` 的问题（加全模式兜底）

## [0.3.0] - 2026-09-11

### Added

- **`CoverGenerator` 模块**：21:9 主封面 + 1:1 方图，深色 Editorial 杂志风格
- **`SocialCardGenerator` 模块**：5 个平台规格（xhs / wechat-cover / wechat-article / weibo / generic）
- **`DesignAuditor` 模块**：三门质量审计（主题合理性 / 视觉密度 / 可编辑交付）
- **`CoverAdvisor` 模块**：6 种高转化封面模式智能推荐
- **4 套卡片视觉风格**：Swiss 极简 / Editorial 杂志 / Clean Light 浅色 / Dark Bold 深色
- **22 个新测试**覆盖全部视觉模块

## [0.2.0] - 2026-09-10

### Added

- **`ContentSearcher` 模块**：GitHub API 搜索 + web/custom 适配器，选题灵感发现
- **`DraftGenerator` 模块**：5 种文章风格骨架（tutorial / review / analysis / opinion / general）
- **`generate` 子命令**：Agent 安装后自动生成 Markdown 草稿
- **`search` 子命令**：命令行直接搜索选题
- **12 个新测试**覆盖搜索和生成模块

## [0.1.0] - 2026-09-10

### Added

- **`Pipeline` 核心编排**：MarkdownProcessor → ImageProcessor → CopyCompatValidator 三步流水线
- **`MarkdownProcessor`**：Markdown 转公众号兼容 HTML，7 套排版主题
  - moyu-green / red-white / graphite-minimal / zen-whitespace / moyu-ticket / olive-journal / classic-serif
- **`ImageProcessor`**：PIL 压缩（RGB / 600 宽 LANCZOS / JPEG q82）+ GitHub Contents API CDN 上传
- **`CopyCompatValidator`**：静态扫描 6 类禁忌写法（flex / grid / inline-block / gradient / SVG / base64）
- **Docker 多阶段构建**：builder + runtime 分离，非 root 用户，dumb-init，最终镜像约 120MB
- **docker-compose.yml**：volumes 挂载 input/output/.env
- **GitHub Actions CI**：矩阵测试 Python 3.11/3.12 + Docker 构建验证
- **12 个核心测试**覆盖 Processor 和 Validator
