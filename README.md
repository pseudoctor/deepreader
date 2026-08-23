# Deepreader

[![Checks](https://github.com/pseudoctor/deepreader/actions/workflows/check.yml/badge.svg?branch=main)](https://github.com/pseudoctor/deepreader/actions/workflows/check.yml)
[![Windows Package](https://github.com/pseudoctor/deepreader/actions/workflows/windows-build.yml/badge.svg?branch=main)](https://github.com/pseudoctor/deepreader/actions/workflows/windows-build.yml)

> 本地优先的 AI 深度阅读应用，帮助你理解、复述、提问、复习和应用书籍及长文档。

当前版本：`0.0.1`

Deepreader 将 Python 后端、Web 前端和 Electron 桌面端组合成一个可持续使用的阅读工作区。它强调主动阅读、证据绑定和个人理解沉淀，而不是一次性生成摘要。

## 功能

- 读前导览、章节精读和苏格拉底式提问
- 费曼复述检查和主动回忆卡片
- 证据绑定阅读卡、图尔敏论证分析和 X-Ray 深拆
- 多书/多文档主题地图、概念图和跨章节综合
- Markdown 笔记、复习材料和 Obsidian 导出
- Local Mock、OpenAI、Claude、Gemini、DeepSeek、Qwen 等 Provider
- Web、Electron 桌面端和 Python CLI

## 下载

### Windows

推送代码后，GitHub Actions 会在 Windows runner 上构建 `.exe`。打开 [Windows Package workflow](https://github.com/pseudoctor/deepreader/actions/workflows/windows-build.yml)，进入具体运行记录，从 `Artifacts → deep-reading-windows` 下载。

### macOS

macOS DMG 当前通过本地打包生成；构建命令和签名说明见[打包与发布](#打包与发布)。

## 快速开始

### 启动桌面端

在仓库根目录执行：

```bash
make install-dev
npm ci --prefix apps/web
npm ci --prefix apps/desktop
make desktop-dev
```

桌面端会启动自己的本地后端，并自动选择可用端口。

### 启动 Web/API

如果需要分别运行 API 和 Web：

```bash
make install-dev
npm ci --prefix apps/web
make api-dev
make web-dev
```

默认地址：

- API health check：<http://127.0.0.1:8000/health>
- Web app：<http://127.0.0.1:5173/>

如需连接已有 API：

```bash
DEEP_READING_API_BASE_URL=http://127.0.0.1:8000 make desktop-dev
```

## 配置

Web 和桌面端都可以从顶部导航栏的 `Settings / 设置` 配置模型 Provider、Model、Base URL 和 API Key。

- Web/API 本地开发设置写入 `.deep-reading-local/llm_settings.json`
- 桌面端设置写入 Electron `userData` 目录下的 `llm_settings.json`
- 这些位置已被 Git 忽略，API Key 不会写入源码
- 推荐模型列表位于 `scripts/deep_reading/model_catalog.json`

支持的 Provider：

- Local Mock
- OpenAI-compatible
- Claude
- Gemini
- DeepSeek
- Qwen

## 使用流程

### 1. 初始化阅读工作区

可以在应用中操作，也可以让支持本地工具调用的 AI 执行：

```text
用 Deepreader 初始化这本书：~/Books/example.pdf
```

工作区通常包含：

```text
example-reading/
├── metadata.json
├── reading_state.json
├── reading-plan.md
├── book_map.md
├── chapter_notes/
├── questions.md
├── concept_map.md
├── review_cards.md
├── evidence_cards.md
├── argument_maps.md
├── xray_notes.md
├── napkin.md
├── multi_source_map.md
└── source_text/full_text.txt
```

### 2. 选择阅读路线

```text
用 Deepreader 看一下这本书有哪些章节，并建议阅读路线。
```

### 3. 章节陪读

推荐每章按以下顺序推进：

1. AI 提出读前问题。
2. 你阅读章节原文或相关摘录。
3. AI 解释核心问题和论证结构。
4. AI 进行苏格拉底式提问。
5. 你用 3–5 句话复述。
6. AI 做费曼复述检查。
7. 双方沉淀章节笔记和复习卡片。

示例：

```text
用 Deepreader 带我读 ch01，先给我 5 个 read-for questions。
```

```text
这是我对 ch01 的总结：…… 请用 Feynman check 帮我纠偏。
```

### 4. 沉淀和综合

读完一章后，可以更新：

- `chapter_notes/`
- `questions.md`
- `review_cards.md`
- `concept_map.md`
- `personal_insights.md`
- `evidence_cards.md`

每读完几章，可以继续请求：

```text
基于 ch01 到 ch03，帮我总结作者目前的核心论证链条。
```

```text
把 ch05 的思想应用到我当前的数据库设计里，区分书中原意和你的推断。
```

## 高级阅读模式

| 模式 | 适用场景 | 主要产物 |
| --- | --- | --- |
| 证据绑定阅读 | 学术书、技术书、争议性观点 | `evidence_cards.md` |
| 图尔敏论证分析 | 哲学、管理、政策和理论书 | `argument_maps.md` |
| X-Ray 深拆 | 章节、部分或整本书的结构提取 | `xray_notes.md` |
| 餐巾纸压缩 | 对 X-Ray 结果做极限压缩 | `napkin.md` |
| 多源主题地图 | 比较多本书、论文或笔记 | `multi_source_map.md` |

示例：

```text
为 ch02 的核心观点生成 evidence cards，每条都要有 source locator、support、confidence 和 not explicit。
```

```text
用 Toulmin model 分析 ch03 的核心论证，并指出隐含假设和弱点。
```

## 笔记与 Obsidian

阅读过程中可以追加结构化笔记：

```bash
python3 scripts/reading_workspace.py note <workspace> ch01 --section "Confusions" --text "这里记录困惑"
python3 scripts/reading_workspace.py insight <workspace> --text "这里记录个人启发"
python3 scripts/reading_workspace.py review-card <workspace> --question "问题" --answer "答案"
python3 scripts/reading_workspace.py evidence <workspace> --claim "主张" --locator "ch01/page 3" --support "证据说明" --confidence Medium
```

导出到 Obsidian：

```bash
python3 scripts/reading_workspace.py export-obsidian <workspace> --vault-folder ~/ObsidianVault/Reading/example
```

该命令会复制 Markdown 笔记、保留目录结构，并生成 `index.md` 入口页。

## CLI 参考

以下命令从仓库根目录运行：

<details>
<summary>展开 CLI 命令</summary>

初始化和状态：

```bash
python3 scripts/reading_workspace.py init ~/Books/example.pdf --workspace ~/Books/example-reading
python3 scripts/reading_workspace.py list ~/Books/example-reading
python3 scripts/reading_workspace.py status ~/Books/example-reading
python3 scripts/reading_workspace.py chapter ~/Books/example-reading ch01
python3 scripts/reading_workspace.py source ~/Books/example-reading
python3 scripts/reading_workspace.py library ~/Books/example-reading
```

模板和章节状态：

```bash
python3 scripts/reading_workspace.py template ~/Books/example-reading evidence
python3 scripts/reading_workspace.py template ~/Books/example-reading argument
python3 scripts/reading_workspace.py template ~/Books/example-reading xray
python3 scripts/reading_workspace.py template ~/Books/example-reading napkin
python3 scripts/reading_workspace.py mark ~/Books/example-reading ch01 --state reading
python3 scripts/reading_workspace.py mark ~/Books/example-reading ch01 --state done
python3 scripts/reading_workspace.py mark ~/Books/example-reading ch01 --state review
```

</details>

## 支持格式

- PDF
- EPUB
- DOCX
- TXT
- Markdown
- HTML
- RTF

解析会根据本地依赖选择不同实现；缺少高质量解析库时会使用 fallback。

## 开发与验证

主要目录：

```text
apps/web/       # React + Vite 前端
apps/desktop/   # Electron 桌面端
scripts/        # Python 后端和 CLI
tests/          # Python 测试
```

常用命令：

```bash
make lint    # Ruff 静态检查
make format  # Ruff 格式化
make test    # Python 测试
make check   # Python + Web + Desktop 验证
make clean   # 清理本地虚拟环境和测试缓存
```

GitHub Actions 会在 push 和 pull request 时运行 `.github/workflows/check.yml`。

## 打包与发布

### macOS DMG

```bash
make desktop-dist-mac
```

产物位于 `apps/desktop/release/*.dmg`。当前未配置 Apple Developer ID，DMG 未签名。

### Windows EXE

推荐推送后使用 [Windows Package workflow](https://github.com/pseudoctor/deepreader/actions/workflows/windows-build.yml) 构建，并从 Actions artifact 下载。

Windows 本机打包：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
npm ci --prefix apps/web
npm ci --prefix apps/desktop
npm run dist:win --prefix apps/desktop
```

产物位于 `apps/desktop/release/*.exe`，当前版本的文件名以 `Deepreader-0.0.1` 开头。`release/` 已被 Git 忽略，不会随源码提交。

## License

[MIT](LICENSE)
