# Deepreader

[![Checks](https://github.com/pseudoctor/deepreader/actions/workflows/check.yml/badge.svg?branch=main)](https://github.com/pseudoctor/deepreader/actions/workflows/check.yml)
[![Windows Package](https://github.com/pseudoctor/deepreader/actions/workflows/windows-build.yml/badge.svg?branch=main)](https://github.com/pseudoctor/deepreader/actions/workflows/windows-build.yml)

> 本地优先的 AI 深度阅读工作区：把书籍和长文档变成可逐章阅读、追溯证据、主动回忆和持续复习的材料。

Deepreader 将 Python 后端、Web 界面、Electron 桌面端和命令行工具放在同一个仓库中。源文件、阅读状态和笔记保存在本地；是否调用云端模型、调用哪个 Provider，由你的配置决定。

## 适合什么场景

- 开始阅读一本书或一组长文档，需要先建立章节地图和阅读路线。
- 逐章精读，希望用问题、复述和 Feynman 检查验证自己是否真正理解。
- 需要把关键主张绑定到来源位置，而不是只保存一段脱离上下文的摘要。
- 需要比较多本书、论文或笔记，整理概念、论证和证据之间的关系。
- 想把阅读过程沉淀为 Markdown 笔记、复习卡片或 Obsidian 知识库。

## 能做什么

### 阅读与理解

- 初始化单个文件、目录或 glob 匹配到的多个来源。
- 自动提取章节、生成阅读计划、章节笔记和阅读状态。
- 逐章阅读、苏格拉底式提问、主动回忆和 Feynman 复述检查。
- 对选中文本进行解释、追问和基于来源的证据检索。

### 证据与综合

- 证据卡：主张、来源定位、支持说明、置信度、未明确内容和推断。
- Toulmin 风格论证图：Claim、Grounds、Warrant、Backing、Qualifier 和 Rebuttal。
- 证据表、概念图、全书一页总结、X-Ray 深拆和 Napkin 压缩。
- 多源主题地图、跨章节综合、弱概念记录和间隔复习。

### 工作区与导出

- Web、Electron 桌面端和 Python CLI 共用同一套阅读工作区格式。
- 工作区使用 Markdown、JSON 和纯文本保存，便于检查、备份和版本控制。
- 支持导出到 Obsidian，并保留章节笔记与内部链接。

## 快速开始

### 环境要求

- Python 3.11 或更高版本。
- Node.js 和 npm；CI 使用 Node.js 22。
- 运行 PDF 提取时，优先安装 Poppler 的 `pdftotext`；没有它时，程序会尝试可用的 Python PDF 解析器。

### 安装开发依赖

在仓库根目录执行：

```bash
make install-dev
npm ci --prefix apps/web
npm ci --prefix apps/desktop
```

`make install-dev` 会创建 `.venv` 并安装 Python 开发依赖。前端和桌面端依赖分别由两个 lockfile 管理。

### 启动 Web/API

终端一：

```bash
make api-dev
```

终端二：

```bash
make web-dev
```

默认地址：

- Web：<http://127.0.0.1:5173/>
- API 健康检查：<http://127.0.0.1:8000/health>

Web 开发服务器会把 `/api` 请求代理到 `http://127.0.0.1:8000`。

### 启动 Electron 桌面端

桌面端开发模式需要 Web 开发服务器先运行：

```bash
make web-dev
```

再打开另一个终端：

```bash
make desktop-dev
```

桌面端会自动检查 `.venv` 中的后端依赖，启动一个本地 API，并选择可用端口。若设置了 `DEEP_READING_API_BASE_URL` 连接已有 API，则还必须设置 `DEEP_READING_API_TOKEN`；API 请求会通过 `X-Deep-Reading-API-Token` 校验。

## 第一次阅读

### 1. 创建工作区

CLI 支持文件、目录和 glob。使用仓库创建的虚拟环境运行：

```bash
.venv/bin/python scripts/reading_workspace.py init \
  ~/Books/example.pdf \
  --workspace ~/Books/example-reading
```

Windows PowerShell 对应命令：

```powershell
.venv\Scripts\python.exe scripts\reading_workspace.py init `
  "$HOME\Books\example.pdf" `
  --workspace "$HOME\Books\example-reading"
```

初始化会生成来源元数据、全文、章节状态、阅读计划、章节笔记、问题、概念图、复习卡、证据卡、论证图、X-Ray、Napkin、多源地图和 `library.json`。完整的工作区标记与生成逻辑见 [`scripts/deep_reading/workspace.py`](scripts/deep_reading/workspace.py)。

也可以直接在 Web 或桌面端选择来源文件和工作区目录创建。

### 2. 选择阅读路线

先查看工作区状态和章节列表：

```bash
WORKSPACE=~/Books/example-reading

.venv/bin/python scripts/reading_workspace.py status "$WORKSPACE"
.venv/bin/python scripts/reading_workspace.py list "$WORKSPACE"
```

根据目标选择路线：

| 目标 | 建议顺序 |
| --- | --- |
| 快速建立全貌 | `status` → `source` → `chapter` |
| 深度学习 | 章节阅读 → 问题 → 自己复述 → Feynman 检查 → 复习卡 |
| 研究或写作 | 章节阅读 → 证据卡 → 论证图 → 证据核验 |
| 多书比较 | 分别初始化工作区 → `library` → 多源地图 → 冲突与证据缺口 |
| 结构提取 | `template xray` → 深拆 → `template napkin` |

不要把章节标题或自动提取结果当成完整理解；先用它们确定下一段要读什么，再回到原文核对。

### 3. 逐章阅读

推荐每章按这个循环推进：

1. 先回答本章要解决什么问题。
2. 带着 3–7 个 read-for questions 阅读原文。
3. 提取主张、概念、证据、假设和边界。
4. 不看原文复述 3–5 句话。
5. 用 Feynman 检查找出模糊点、缺失因果链和无依据跳跃。
6. 保存证据卡、章节笔记和下一次复习的问题。

示例请求：

```text
用 Deepreader 带我读 ch01，先给我 5 个 read-for questions。
```

```text
这是我对 ch01 的总结：…… 请做 Feynman check，指出缺失的因果链。
```

## AI Provider 配置

Web 和桌面端都可以从顶部的 `Settings / 设置` 配置 Provider、Model、Base URL 和 API Key。可用 Provider 由 `scripts/deep_reading/llm.py` 中的 `PROVIDER_SPECS` 定义，推荐模型目录位于 [`scripts/deep_reading/model_catalog.json`](scripts/deep_reading/model_catalog.json)。

| Provider | API Key 环境变量 | 说明 |
| --- | --- | --- |
| Local Mock | 无 | 不需要远程 API，适合本地开发和界面验证。 |
| OpenAI | `OPENAI_API_KEY` | 默认使用 OpenAI 兼容接口配置。 |
| Claude | `ANTHROPIC_API_KEY` | 使用 Anthropic API。 |
| Gemini | `GEMINI_API_KEY` | 使用 Google Generative Language API。 |
| DeepSeek | `DEEPSEEK_API_KEY` | 支持自定义 Base URL。 |
| Qwen | `QWEN_API_KEY` | 支持 DashScope 兼容接口。 |

默认的 Web/API 设置写入被 Git 忽略的 `.deep-reading-local/llm_settings.json`。桌面端将设置写入 Electron 的 `userData` 目录。不要把 API Key 写进源码、README 或提交记录。

## CLI 参考

显示所有命令：

```bash
.venv/bin/python scripts/reading_workspace.py --help
```

常用命令：

| 命令 | 用途 |
| --- | --- |
| `init <source>` | 提取来源并创建阅读工作区。 |
| `status <workspace>` | 查看来源、字数、章节进度和主要产物。 |
| `list <workspace>` | 以表格形式列出章节及状态。 |
| `source <workspace>` | 查看来源处理记录。 |
| `library <workspace>` | 查看工作区的来源库信息。 |
| `chapter <workspace> <chapter-id>` | 输出章节笔记。 |
| `chapter-text <workspace> <chapter-id>` | 输出章节原文。 |
| `mark <workspace> <chapter-id> --state <state>` | 更新章节状态。可用状态包括 `not-started`、`reading`、`done`、`review` 和 `weak`。 |
| `template <workspace> <name>` | 输出 `evidence`、`argument`、`xray`、`napkin`、`review` 或 `concept` 模板。 |
| `note <workspace> <chapter-id>` | 添加章节笔记。 |
| `insight <workspace>` | 添加个人启发。 |
| `review-card <workspace>` | 添加问题和答案形式的复习卡。 |
| `evidence <workspace>` | 添加带 locator 和 confidence 的证据卡。 |
| `export-obsidian <workspace>` | 将工作区导出到指定 Obsidian 文件夹。 |

示例：

```bash
.venv/bin/python scripts/reading_workspace.py mark "$WORKSPACE" ch01 --state reading

.venv/bin/python scripts/reading_workspace.py note "$WORKSPACE" ch01 \
  --section "Confusions" \
  --text "记录这里没有解释清楚的概念"

.venv/bin/python scripts/reading_workspace.py evidence "$WORKSPACE" \
  --claim "作者关于反馈循环的主张" \
  --locator "ch01 / section 2" \
  --support "用自己的话记录支持理由" \
  --confidence Medium \
  --not-explicit "作者没有直接说明的边界" \
  --inference "我的推断"

.venv/bin/python scripts/reading_workspace.py export-obsidian "$WORKSPACE" \
  --vault-folder ~/ObsidianVault/Reading/example
```

## 支持的来源格式

当前支持：

- PDF
- EPUB
- DOCX
- TXT / TEXT
- Markdown：`MD` / `MARKDOWN`
- HTML：`HTML` / `HTM`
- RTF

可以传入一个文件、目录或 glob。目录会递归查找支持的扩展名；无法提取的来源会记录在工作区的 `sources.md`，而不是静默消失。

## 开发与验证

目录职责：

```text
apps/web/       # React + Vite Web 界面
apps/desktop/   # Electron 桌面端
scripts/        # Python 后端、CLI 和工作区逻辑
tests/          # Python 测试
references/     # 阅读流程和输出模板
```

常用命令：

```bash
make lint      # Ruff 静态检查
make format    # Ruff 格式化
make test      # Python 测试
make check     # Python、Web 和桌面端验证
make clean     # 清理本地虚拟环境和测试缓存
```

CI 在 push 和 pull request 时运行 [`make check`](.github/workflows/check.yml)。如果只改 Python，优先运行 `make lint` 和 `make test`；如果改了 Web 或 Electron，再运行 `make check`。

## 打包

### macOS

构建未签名的目录包：

```bash
make desktop-package-mac
```

构建 DMG 和 ZIP：

```bash
make desktop-dist-mac
```

产物写入 `apps/desktop/release/`。macOS 打包配置启用了 notarization，并需要对应的 Apple Developer 配置；没有配置时请先检查：

```bash
make desktop-signing-check
```

### Windows

本地构建 NSIS 安装包：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
npm ci --prefix apps\web
npm ci --prefix apps\desktop
npm run dist:win --prefix apps\desktop
```

也可以推送代码后使用 [Windows Package workflow](https://github.com/pseudoctor/deepreader/actions/workflows/windows-build.yml)，从运行记录的 `Artifacts → deep-reading-windows` 下载构建产物。

所有产物都写入 `apps/desktop/release/`，文件名由 `apps/desktop/package.json` 的 `artifactName` 规则生成，不要在文档中手工记录某个版本号。

## Agent 集成

仓库根目录的 [`SKILL.md`](SKILL.md) 是面向 AI agent 的深度阅读工作流说明，规定了主动阅读、证据绑定、论证分析、复习和应用阅读的边界。它与应用代码共享同一套工作区和 CLI 入口。

## License

[MIT](LICENSE)
