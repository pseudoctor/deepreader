# Deep Reading Skill 使用说明

`deep-reading` 是一个 AI 深度阅读教练 skill，用来帮助你深入阅读、理解、复述、提问、复习和应用一本书或一组长文档。

它不是图书管理工具，也不是简单总结工具。它的目标是把一本书变成一个可持续陪读的阅读工作区，让 AI 带你完成：

- 读前导览
- 章节精读
- 苏格拉底式提问
- 费曼复述检查
- 证据绑定阅读卡
- 图尔敏论证分析
- 三轮 X-Ray 深拆
- 餐巾纸压缩
- 多书/多文档主题地图
- 概念图整理
- 主动回忆卡片
- 跨章节综合
- 应用迁移

## 推荐用法：直接让 AI 操作

正常情况下，你不需要记 Python 命令。直接对 Codex、Claude 或其他支持本地工具调用的 AI 说自然语言即可。

示例：

```text
使用 /Users/armewang/Downloads/deep-reading 这个 skill，帮我初始化 ~/Books/ddia.pdf 的阅读工作区。
```

```text
用 deep-reading 带我读 ch01，先不要总结，先问我阅读前问题。
```

```text
用 deep-reading 检查我对 ch02 的总结。
```

```text
用 deep-reading 给 ch03 生成主动回忆题和复习卡片。
```

```text
用 deep-reading 总结 ch01-ch03 的概念关系。
```

```text
用 deep-reading 把这章内容应用到我的项目/论文/代码里。
```

```text
用 deep-reading 对这本书做 x-ray 深拆：骨架扫描、论证解剖、灵魂提取。
```

```text
用 deep-reading 给 ch04 做图尔敏论证分析，标出 Claim、Grounds、Warrant、Rebuttal。
```

```text
用 deep-reading 为 ch05 的关键主张生成 evidence cards，标明来源位置和不确定性。
```

```text
用 deep-reading 把这个文件夹里的几本书做成 multi-source map，比较它们的共识和分歧。
```

AI 会根据 skill 自动执行必要的本地脚本，例如初始化工作区、读取章节笔记、查看阅读状态、更新进度等。

## 当前应用入口

本项目现在同时包含 Python 后端、Web 前端和 Electron 桌面端：

```bash
make install-dev
make web-install
make desktop-install
make api-dev
make web-dev
```

开发时通常打开：

- API health check: `http://127.0.0.1:8000/health`
- Web app: `http://127.0.0.1:5173/`

桌面端开发：

```bash
make desktop-dev
```

桌面端默认会启动自己的本地后端，并使用随机可用端口，避免误连到其他
`127.0.0.1:8000` 服务。如需显式连接已有 API，可设置：

```bash
DEEP_READING_API_BASE_URL=http://127.0.0.1:8000 make desktop-dev
```

## 桌面端打包

macOS DMG：

```bash
make desktop-dist-mac
```

产物位于 `apps/desktop/release/*.dmg`。当前未配置 Apple Developer ID，生成的 DMG 未签名。

Windows `.exe` 推荐使用 GitHub Actions：推送代码后，打开 `Actions → Windows Package`，在运行结果的
`Artifacts → deep-reading-windows` 下载构建产物；也可以手动触发 workflow。

在 Windows 本机打包：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
npm ci --prefix apps/web
npm ci --prefix apps/desktop
npm run dist:win --prefix apps/desktop
```

Windows 产物位于 `apps/desktop/release/*.exe`。构建产物目录已被 Git 忽略，不会随源码提交；请通过 GitHub Actions artifact 或 GitHub Release 分发。

## AI Provider 设置

Web 和桌面端都通过顶部导航栏的 `Settings / 设置` 打开模型设置。当前预留并支持：

- Local Mock
- OpenAI
- Claude
- Gemini
- DeepSeek
- Qwen

设置项包括 Provider、Model、Base URL 和 API Key。API Key 保存后不会在界面回显。
Web/API 本地开发默认写入 `.deep-reading-local/llm_settings.json`，该目录已被 git 忽略。
桌面端启动的后端默认写入 Electron `userData` 目录下的 `llm_settings.json`，避免把桌面端密钥落在项目目录中。
后续仍可以继续迁移到 Electron `safeStorage` 或系统 Keychain。

推荐模型列表位于：

```text
scripts/deep_reading/model_catalog.json
```

有 API Key 时，支持 OpenAI-compatible 和 Gemini provider 尝试刷新远端模型列表；
远端不可用时回退到本地推荐列表，也可以在 Model 输入框中手动输入模型名。

## 开发与验证

本项目的 Python 入口仍然保持兼容：

```bash
python3 scripts/reading_workspace.py --help
```

模块化后的核心代码位于：

```text
scripts/deep_reading/
```

推荐使用 `.python-version` 中声明的 Python 版本。当前开发验证命令为：

```bash
make install-dev
make check
```

常用开发命令：

```bash
make lint    # 运行 ruff 静态检查
make format  # 运行 ruff 代码格式化
make test    # 只运行测试
make check   # Python + Web + Desktop 验证
make clean   # 清理本地虚拟环境和测试缓存
```

如果托管到 GitHub，`.github/workflows/check.yml` 会在 push 和 pull request 时运行同一套检查：

```bash
make check
```

## 边读边记笔记

初始化工作区后，可以在阅读过程中直接追加结构化笔记：

```bash
python3 scripts/reading_workspace.py note <workspace> ch01 --section "Confusions" --text "这里记录困惑"
python3 scripts/reading_workspace.py insight <workspace> --text "这里记录个人启发"
python3 scripts/reading_workspace.py review-card <workspace> --question "问题" --answer "答案"
python3 scripts/reading_workspace.py evidence <workspace> --claim "主张" --locator "ch01/page 3" --support "证据说明" --confidence Medium
```

`note` 会写入对应章节笔记的二级标题下；`insight`、`review-card` 和 `evidence`
分别写入 `personal_insights.md`、`review_cards.md`、`evidence_cards.md`。

## 导出到 Obsidian

如果阅读工作区不在 Obsidian Vault 内，可以把 Markdown 笔记导出到指定文件夹：

```bash
python3 scripts/reading_workspace.py export-obsidian <workspace> --vault-folder ~/ObsidianVault/Reading/example
```

该命令会复制所有 Markdown 笔记，保留 `chapter_notes/` 等目录结构，并生成一个
`index.md` 作为 Obsidian 入口页。同名 Markdown 文件会被当前工作区版本覆盖。

## 第一步：初始化阅读工作区

对 AI 说：

```text
用 deep-reading 初始化这本书：~/Books/example.pdf
```

AI 会创建一个阅读工作区，通常类似：

```text
example-reading/
  metadata.json
  reading_state.json
  reading-plan.md
  book_map.md
  chapter_notes/
  questions.md
  concept_map.md
  review_cards.md
  personal_insights.md
  evidence_cards.md
  argument_maps.md
  xray_notes.md
  napkin.md
  multi_source_map.md
  sources.md
  library.json
  source_text/full_text.txt
```

## 第二步：查看章节并选择阅读路线

你可以说：

```text
用 deep-reading 看一下这本书有哪些章节，并建议阅读路线。
```

或者：

```text
我想深度读这本书，帮我制定一个按章节推进的阅读计划。
```

AI 会读取 `book_map.md`、`metadata.json` 和 `reading-plan.md`，然后给出阅读建议。

## 第三步：开始章节陪读

推荐每章按这个顺序读：

1. AI 先提出读前问题。
2. 你阅读章节原文或相关摘录。
3. AI 解释章节核心问题和论证结构。
4. AI 对你进行苏格拉底式提问。
5. 你用 3-5 句话复述。
6. AI 做费曼复述检查。
7. AI 帮你沉淀章节笔记和复习卡片。

可以这样说：

```text
用 deep-reading 带我读 ch01。先给我 5 个 read-for questions。
```

```text
现在对我进行苏格拉底式提问，检查我是否真的理解 ch01。
```

```text
这是我对 ch01 的总结：…… 请用 Feynman check 帮我纠偏。
```

## 第四步：沉淀笔记和复习材料

读完一章后，可以让 AI 更新：

- `chapter_notes/chXX-*.md`
- `questions.md`
- `review_cards.md`
- `concept_map.md`
- `personal_insights.md`

示例：

```text
基于我们刚才的讨论，更新 ch01 的章节笔记。
```

```text
为 ch01 生成 10 张主动回忆卡片，写入 review_cards.md。
```

```text
把 ch01 的核心概念加入 concept_map.md。
```

## 第五步：跨章节综合

每读完几章，建议做一次综合。

示例：

```text
基于 ch01 到 ch03，帮我总结作者目前的核心论证链条。
```

```text
ch02 和 ch03 的概念有什么关系？哪些地方容易误解？
```

```text
帮我更新 concept_map.md，把前三章的概念关系画出来。
```

## 第六步：应用迁移

如果你希望把书用于项目、写作、研究或决策，可以说：

```text
基于目前读过的章节，提取对我这个项目有用的 5 条决策规则。
```

```text
把 ch05 的思想应用到我当前的数据库设计里，区分书中原意和你的推断。
```

```text
这本书目前读到的内容，对我的论文选题有什么启发？
```

AI 应该明确区分：

- 书中明确表达的内容
- AI 的解释和推断
- 针对你个人场景的建议

## 高级阅读模式

### 证据绑定阅读

适合学术书、技术书、争议性观点、需要引用的材料。

```text
为 ch02 的核心观点生成 evidence cards。每条都要有 source locator、support、confidence 和 not explicit。
```

产物通常写入：

```text
evidence_cards.md
```

### 图尔敏论证分析

适合论证型章节：哲学、管理、商业、社会科学、评论、政策、理论书。

```text
用 Toulmin model 分析 ch03 的核心论证，并指出隐含假设和弱点。
```

产物通常写入：

```text
argument_maps.md
```

### X-Ray 深拆

适合读完一章、一部分或整本书后做深度结构提取。

```text
对 ch01-ch05 做 x-ray：第一轮骨架扫描，第二轮血肉解剖，第三轮灵魂提取。
```

产物通常写入：

```text
xray_notes.md
```

### 餐巾纸压缩

适合在 X-Ray 后做极限压缩。

```text
把这本书压缩成一个公式、一句话、一张 ASCII 图和一个行动触发器。
```

产物通常写入：

```text
napkin.md
```

### 多源主题地图

适合一个文件夹里有多本书、论文或笔记。

```text
基于这个 reading workspace，做 multi-source map：列出核心概念、共识、冲突、概念谱系和证据缺口。
```

产物通常写入：

```text
multi_source_map.md
```

## 手动命令备查

这些命令主要给 AI 自动调用。只有当你想手动操作，或 AI 没有本地执行权限时，才需要自己运行。

初始化阅读工作区：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py init ~/Books/example.pdf --workspace ~/Books/example-reading
```

查看章节列表：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py list ~/Books/example-reading
```

查看阅读状态：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py status ~/Books/example-reading
```

查看某章笔记模板：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py chapter ~/Books/example-reading ch01
```

查看来源清单：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py source ~/Books/example-reading
```

查看 library 元数据：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py library ~/Books/example-reading
```

输出某类模板：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py template ~/Books/example-reading evidence
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py template ~/Books/example-reading argument
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py template ~/Books/example-reading xray
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py template ~/Books/example-reading napkin
```

标记章节状态：

```bash
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py mark ~/Books/example-reading ch01 --state reading
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py mark ~/Books/example-reading ch01 --state done
python3 /Users/armewang/Downloads/deep-reading/scripts/reading_workspace.py mark ~/Books/example-reading ch01 --state review
```

## 支持格式

当前脚本支持：

- PDF
- EPUB
- DOCX
- TXT
- Markdown
- HTML
- RTF

PDF、EPUB、DOCX 等格式会根据本地依赖情况使用不同提取方式。如果缺少高质量解析库，脚本会尽量使用 fallback。

## 最佳实践

- 不要急着让 AI 总结整本书。
- 每次只推进一章或一个小节。
- 先回答问题，再看 AI 的解释。
- 每章都写自己的 3-5 句复述。
- 让 AI 检查你的理解，而不是只给你标准答案。
- 对关键结论要求证据绑定，避免 AI 把推断说成原文。
- 对论证型章节使用图尔敏模型，主动找隐含假设和边界。
- 每个部分结束后做一次 X-Ray 深拆。
- 全书结束后做餐巾纸压缩。
- 每 3 章做一次综合。
- 把真正有用的理解沉淀到 `chapter_notes/`、`evidence_cards.md`、`argument_maps.md`、`concept_map.md` 和 `review_cards.md`。

一句话：脚本负责建立和维护阅读工作区，`deep-reading` skill 负责陪你读、问你问题、检查理解、沉淀笔记。
