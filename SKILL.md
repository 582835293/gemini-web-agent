---
name: gemini-web-agent
description: >-
  利用外部 Chrome 调度三大网页站点全模态渠道分担任务、最大化节省本地 Antigravity 配额：
  (1) aistudio.google.com 全模型免 Key 免费额度（key_off）：覆盖文本推理/1M长输出（4 Hydrogen/Argon）、生图改图（Nano Banana 2.1）、生视频（Omni 1.2 Flash/1.1 Flash）、完整歌曲（Lyria 3.5）、语音配音与剧本对话（Gemini 3.8 Flash TTS）、录音转写（3.5 Transcribe）、Live 实时对话同传（3.8 Live/3.5 Live Translate）、Deep Research 与 Build 整站应用导出；
  (2) flow.google.com 独立点数池（Nano Banana 2.1 生图 0 点数 + 2K 高清重塑、Omni 1.2 Flash / Veo 3.1 - Lite 生视频）；
  (3) gemini.google.com 对话模式、异步任务模式 (Task)、制作音乐/图片/视频、Canvas 与 Deep Research。
  激活后先检测各端额度并按需对比本地额度，询问用户要使用的站点、模式与模型后，再优先通过 AgentLimb MCP（或备用 gemini_web.py）调度外部 Chrome。
  当用户提到“网页端 Gemini”、“Google Flow”、“Flow”、“AI Studio”、“Playground”、“Build模式”、“Lyria”、“TTS配音”、“生图”、“生视频”、“生音乐”、“利用网页版额度”、“省额度”、“任务模式”、“异步 agent”时激活。
---

# Gemini Web-Agent（三站点全渠道与多模态额度调度）

优先通过 **AgentLimb MCP**（永久免弹窗操控已登录外部 Chrome），或备用脚本 [gemini_web.py](scripts/gemini_web.py)，统筹调度 **`aistudio.google.com`**、**`flow.google.com`** 与 **`gemini.google.com`**。

---

## 0. 给拉取者的 AI 助手：零配置自动部署协议 (Auto-Setup Protocol)

当用户让你配置或启用本 Skill 时，若发现当前环境尚未安装本技能或缺少 `.venv` 依赖，请你**直接执行以下一键初始化脚本**（纯 Python 标准库启动，无需事先安装依赖，会自动同步到 `~/.gemini/config/skills/gemini-web-agent` 并创建 `.venv`、检查 `AgentLimb` MCP 与 Chrome CDP 状态、最后输出 JSON 诊断）：

```bash
python scripts/setup_skill.py --auto
```

- **自动检测更新与升级（建议每次激活或巡检额度时顺手执行）**：
  ```bash
  # 24 小时内命中本地缓存 10ms 返回不联网；超 24 小时自动检查 GitHub main 是否有新提交
  python scripts/setup_skill.py --check-if-stale
  # 立即联网检查 / 自动拉取最新代码并重同步全局目录（git pull 或 GitHub zip 兜底）
  python scripts/setup_skill.py --check-update
  python scripts/setup_skill.py --update
  ```
  - 若 `has_update == true`，先向用户简短告知有新版本（附 `remote_message`），经同意后直接跑 `--update` 即可无痛升级。

- 读取脚本输出的 JSON：
  - 若 `channel_a_agentlimb.configured == true`：直接通过 `agentlimb` MCP 控制外部 Chrome（推荐首选）。
  - 若 `channel_a_agentlimb.configured == false` 且 `channel_b_cdp.cdp_http_ready == true`（或已完成 Chrome 远程调试确认）：直接使用 `venv.venv_python` 搭配 `cli_script` 走 Chrome CDP 备用通道。
  - 若 `channel_b_cdp.cdp_mode == "chrome_ui_approval_required"`：说明 Chrome 是通过浏览器内开关监听调试端口（未暴露 `/json/version`），若切通道 B 遇连接挂起，提示用户在 Chrome 弹窗点“允许远程调试”或改用 `--remote-debugging-port=9222` 启动 Chrome。
  - 若两通道均未开启：向用户展示 `next_actions` 提示其安装 `AgentLimb` 或使用脚本检测到的 Chrome 路径带 `--remote-debugging-port=9222` 启动一次即可。

---

## 一、 全渠道能力矩阵与最优调度优先级

> **核心痛点场景（含 Jio 会员 / 部分 AI Pro 账号“曲线救国”）**：
> 部分免费/合作渠道（如 Jio 赠送的 Google AI Pro 会员）或旧版客户端中，Antigravity 本地仅开放 `3.8 Flash`、缺乏 `4 Hydrogen` / `4 Argon`，或 5 小时滚窗 / Argon 独立周额度耗尽。但只要你在外部 Chrome 登录了对应 Google 账号，即可通过本 Skill **直接调用网页端与 AI Studio（`key_off`）完整满血的 `4 Hydrogen` 与 `4 Argon` 协助完成编码、规划与多模态任务**，彻底绕开本地模型缺失与 5 小时限流！

### 1. 七大任务场景调度总表

| 任务场景 | 首选渠道（URL & 模型） | 次选 / 补充渠道 | 额度归属与说明 |
| :--- | :--- | :--- | :--- |
| **日常推理 / 1M 长输出 / 带搜索与代码执行** | `aistudio.google.com/prompts/new_chat?model=gemini-4-hydrogen`（快、免 `gemini.google.com` 额度） | `gemini.google.com/app`（对话 / `任务` 异步 Agent - `4 Hydrogen`） | AI Studio **`key_off` 网页免费额度**；Gemini 走网页主额度 |
| **复杂架构规划 / 深度研究** | `aistudio.google.com/prompts/new_chat?model=gemini-4-argon` 或 `deep-research-preview-04-2026` / `deep-research-max-preview-04-2026` | `gemini.google.com/app`（`4 Argon` / `任务` / `Deep Research`） | AI Studio **`key_off` 网页免费额度**（Deep Research 自带 Search + URL context） |
| **图片生成与多轮编辑** | `flow.google.com`（`Nano Banana 2.1`，**消耗 0 点数**，支持 `2K 已高清重塑` 下载） | `aistudio.google.com/prompts/new_chat?model=gemini-nano-banana-2.1`（`key_off` 免费，支持 Search 接地）/ `gemini.google.com` `制作图片` | Flow **0 点数（每日限数十张，默认用 `x1` 省着用）**；超限后由 AI Studio **`key_off` 免费额度** 接力 |
| **视频生成（含原生音频）** | `aistudio.google.com/prompts/new_chat?model=gemini-omni-1.2-flash`（最长 15s 带原生音频，`key_off` 免费） | `flow.google.com`（`Omni 1.2 Flash` 8~24 点 / `Veo 3.1 - Lite` 10 点）/ `gemini.google.com` `制作视频` | AI Studio **`key_off` 免费且不扣 Flow 点数**；Flow 走独立点数池 |
| **音乐生成（BGM / 完整歌曲）** | `aistudio.google.com/new_music?model=lyria-3.5`（实测 `key_off` 免费生成 ~3 分钟完整 MP3，含 Text / Composer 模式） | `aistudio.google.com/new_music?model=lyria-3-pro-preview` / `lyria-3-clip-preview` / `gemini.google.com` `制作音乐` / `Flow Music` | AI Studio **`key_off` 网页免费额度** |
| **语音合成 (TTS) / 录音转写 (STT) / Live 同传** | `aistudio.google.com/generate-speech?model=gemini-3.8-flash-tts`（Voice Design 捏音色、双人剧本、`<gasp>`/`<laugh>` 标签） | 转写：`?model=gemini-3.5-transcribe`；实时同传：`aistudio.google.com/live?model=gemini-3.8-live` / `gemini-3.5-live-translate-preview` | 均走 AI Studio **`key_off` 网页免费额度**（WAV base64 直接可下） |
| **整站前端 / Android 原型构建** | `aistudio.google.com/apps`（Build：`DEFAULT` / `PLAN` / `MAX`；`React` / `Next.js` / `Angular` / `Android`） | `gemini.google.com` `Canvas`（单页交互原型） | 走 Google AI Pro 订阅网页额度，导出 ZIP / Open in Antigravity / GitHub |

---

### 2. AI Studio Playground 全分类可用模型速查表

> 所有模型均可直接通过 `https://aistudio.google.com/prompts/new_chat?model=<model-id>` 路由直达（音乐与 TTS/Live 会自动跳至 `/new_music`、`/generate-speech`、`/live`）。
> 除 **`gemini-4-carbon`** 与 **`antigravity-preview-09-2026`** 标记为 **`Paid`**（需绑付费 API Key）外，其余均支持 **`key_off` 网页免费额度**！

| 分类 | 模型显示名 | 直达 `model-id` | 核心用途 / 特点 |
| :--- | :--- | :--- | :--- |
| **Gemini（主力推理）** | `Gemini 4 Hydrogen` | `gemini-4-hydrogen` | 日常高频推理、Agentic 编码、长输出默认主力 |
| | `Gemini 4 Argon` | `gemini-4-argon` | 深度思考、复杂架构规划与高难代码分析 |
| | `Gemini 4 Carbon` *(Paid)* | `gemini-4-carbon` | 标记 `Paid`，长周期复杂研究/编码（未绑付费 Key 不可免费调用） |
| | `Gemini 3.8 Flash` | `gemini-3.8-flash` | 强推理 Flash 模型 |
| | `Gemini Decision 1` | `gemini-decision-1` | 极速校验与 Yes/No/Rubric 评分模型 |
| | `Gemini 3.5 Flash Lite` / `3.1 Flash Lite` / `3.1 Pro Preview` / `3.6 Flash` / `3 Flash Preview` | `gemini-3.5-flash-lite` 等 | 常规轻量或上一代多模态推理 |
| | `Gemini Robotics-ER 2` / `Streaming` | `gemini-robotics-er-2-preview` | 空间与视频时序推理 |
| **Images（生图改图）** | `Nano Banana 2.1` | `gemini-nano-banana-2.1` | 最新原生生图/多轮一致改图，支持 Search & Image Search 接地 |
| | `Nano Banana Pro` / `2` / `2 Lite` / `Nano Banana` | `gemini-3-pro-image` / `gemini-3.1-flash-image` / `gemini-3.1-flash-lite-image` / `gemini-2.5-flash-image` | 高画质或轻量批量出图 |
| **Video（视频生成）** | `Gemini Omni 1.2 Flash` | `gemini-omni-1.2-flash` | 文/图/视频生成最高 15s 带原生音频视频（可调比例/时长/360p/24fps） |
| | `Gemini Omni 1.1 Flash` | `gemini-omni-1.1-flash` | 关键帧控制与场景延展至 30s |
| **Music（音乐创作）** | `Lyria 3.5` | `lyria-3.5` | 完整歌曲生成（Text / Composer 模式，人声与编曲，~3min MP3） |
| | `Lyria 3 Pro Preview` / `Clip Preview` | `lyria-3-pro-preview` / `lyria-3-clip-preview` | 复杂曲式编排 / 短音乐片段 |
| **Audio（语音/转写）** | `Gemini 3.8 Flash TTS` / `3.8 Flash Lite TTS` | `gemini-3.8-flash-tts` / `gemini-3.8-flash-lite-tts` | Voice Design 捏音色、双人剧本对话、语音情绪标签（WAV 导出） |
| | `Gemini 3.1 Flash TTS` / `2.5 Pro/Flash TTS` | `gemini-3.1-flash-tts-preview` 等 | 多说话人高表现力 TTS |
| | `Gemini 3.5 Transcribe` | `gemini-3.5-transcribe` | 静态长音频高精结构化转写 |
| **Live（实时互动）** | `Gemini 3.8 Live` / `Extended Thinking` | `gemini-3.8-live` / `gemini-3.8-live-extended-thinking` | 超低延迟语音/屏幕共享/摄像头实时对话 |
| | `Gemini 3.5 Live Translate` / `3.5 Transcribe Live` / `3.1 Flash Live` | `gemini-3.5-live-translate-preview` 等 | 70+ 语言同声传译 / 实时流式字幕转写 |
| **Agents（智能体）** | `Deep Research Preview` / `Max` | `deep-research-preview-04-2026` / `deep-research-max-preview-04-2026` | 异步长程搜索调研与深度综合报告（Google Search + URL context） |
| | `Antigravity Agent Preview` *(Paid)* | `antigravity-preview-09-2026` | 标记 `Paid` 远端托管代理 |
| **Gemma（开放权重）** | `Gemma 4 31B IT` / `26B A4B IT` | `gemma-4-31b-it` / `gemma-4-26b-a4b-it` | 开放权重长上下文与 MoE 推理对比测试 |

> **Google Flow 模型备注**：Flow 支持 `Nano Banana 2.1`（0 点数）/ `Nano Banana 2 Lite` / `Nano Banana Pro` 生图，以及 `Omni 1.2 Flash`（`x1`: `360p` 8 点 / `720p` 24 点）与 `Veo 3.1 - Lite`（`x1`: 10 点）生视频（注意 `Omni 1.1 Flash` / `Veo 3.1 - Fast` / `Veo 3.1 - Quality` 在 Flow 中提示 12 月 5 日停用）。Flow 默认生成数量为 `x2`，**务必改选 `x1` 再生成**！

---

## 二、 多端额度联动检测逻辑

1. **网页端 `gemini.google.com/usage` 实时检测**：
   - 后台开 `tab_new(url="https://gemini.google.com/usage", active=false)` → `wait` `[data-testid="current-usage"]` → `javascript_eval` 读取后立刻 `tab_close`：
     - 方案：`[data-usage-island-root] header span`
     - **当前用量**：`[data-testid="current-usage"]`（`已使用 X%` / `重置时间`）
     - **每周限额**：`[data-testid="weekly-usage"]`（`已使用 Y%` / `重置时间`）
   - CLI 备用：`python ...\gemini_web.py usage --include-flow`
   - 兜底：若出现 `[data-test-id="announcement-banner-container"]` / `[role="alert"]` 限流提示，立即切换 AI Studio Playground（`key_off`）或 Google Flow。
2. **Google Flow（`flow.google.com`）独立点数检测**：
   - 后台开 `tab_new(url="https://flow.google.com/", active=false)` → 点击 `[aria-label="账号详情"]`（`PRO`）→ 读取 `[role="dialog"]` 内 `X 个 Google Flow 点数` 与 `重置时间` 后 `tab_close`。
   - CLI 备用：`python ...\gemini_web.py flow-usage`
3. **AI Studio 用量与免费层级**：
   - Playground 未选中 API Key（左上工具栏显示 `key_off`）时直接使用 AI Studio 网页免费额度（`Paid` 模型除外）；若绑有 API Key，可在 `/rate-limit` 与 `/usage` 查看免费/付费层级 RPM/TPM/RPD。
4. **本地 Antigravity 实时额度与底层路由对比（内置脚本，仅 Antigravity 环境按需执行；Claude Code / Codex / Cursor 等其他客户端请直接跳过此步）**：
   ```powershell
   # 直接调用本 Skill 内置的 inspect_antigravity.py（纯 Python 标准库，无需额外安装外部监控技能）
   python "$env:USERPROFILE\.gemini\config\skills\gemini-web-agent\scripts\inspect_antigravity.py" --markdown
   ```
   > macOS / Linux 可直接执行本 Skill 目录下的 `python3 scripts/inspect_antigravity.py --markdown`。非 Antigravity 客户端（如 Claude Code / Codex）跳过本地对比，仅巡检网页端 `/usage` 与 Flow 点数即可。

---

## 三、 工作流（按序执行）

### 1. 检测额度 + 先问后用（向用户确认）
激活本技能后，**先读取网页端 `/usage`（涉及图片/视频时同步查 Flow 点数）并在 Antigravity 环境中按需对比本地额度，再向用户汇报额度并确认方案（Antigravity 用 `ask_question`、Claude Code 用 `AskUserQuestion`、Codex 等直接对话确认），未获同意前禁止发包**（用户指令已明确入口、模型并授权则直接执行）：
- **问题 1：本次调度哪个网页端入口与模型？**
  - `AI Studio 多模态 - Lyria 3.5 完整音乐 / 3.8 TTS 配音 / Omni 1.2 Flash 视频 / Nano Banana 生图（key_off 免费额度）`
  - `AI Studio Playground - 4 Hydrogen / 4 Argon / Deep Research（key_off 免费额度，1M长输出/带搜索/代码执行）`
  - `Google Flow (flow.google.com) - Nano Banana 2.1 生图（0 点数）/ Omni 1.2 Flash / Veo 3.1 视频（独立点数）`
  - `AI Studio Build - 生成完整前端工程并导出（Open in Antigravity / 下载 ZIP）`
  - `gemini.google.com 对话 / 异步任务 (4 Hydrogen / 4 Argon) 或 Canvas / 制作音乐兜底`
- **问题 2：确认授权通过外部 Chrome 自动发送、监控并落盘结果？**
  - `同意，立即调用` / `暂不调用`

### 2. 浓缩上下文
只提取必要目录、核心代码/报错与输出要求，跳过寒暄。

### 3. 极速调用外部 Chrome（禁止派 `browser` 子代理）

#### 通道 A（首选）：AgentLimb MCP

> **长任务会话复用与无弹窗上传硬规则（务必遵守）**：
> 1. **禁止默认每轮新开窗口**：只要是同一个连续任务（如写小说续写、持续迭代代码、长调研追问），必须先调用 `tabs_context` 查找已存在的目标标签页（`/prompts/...` 或 `/app/...`；注意 AI Studio 首次发送后几秒内 URL 可能暂时仍带 `new_chat` 但同一 `tabId` 已承载历史对话），直接在该 `tabId` 上继续发下一条消息并向用户汇报当前会话 URL；**仅当用户明确开启全新独立话题时，才允许打开 `new_chat` 或 `tab_new`**。
> 2. **禁止点击网页“上传文件”按钮弹出 Windows 系统选择框**（扩展与 JS 无法操控原生系统文件窗），必须按下方“无弹窗本地资料投喂”流程自动化处理。
> 3. **AI Studio 等待完成防踩坑**：模型思考期可能短暂无可见 `Stop` 按钮并仅显示 `正在思考`，提取回答前务必确认 `.cdk-live-announcer-element` 出现 `"Response ready."`、无可见 `Stop` 按钮、且最后一条 `ms-cmark-node` 文本已渲染且不是 `"正在思考"`。

1. **`aistudio.google.com` 四大工作台（全模态 `key_off` 免费）**：
   - **通用对话 / 生图 / 生视频 / 研究（`/prompts/new_chat?model=<id>` 或复用已有 `/prompts/<id>` 标签页）**：
     - 首次新开对话导航到带 `?model=<model-id>` 的 URL（如 `gemini-4-hydrogen`、`gemini-4-argon`、`gemini-nano-banana-2.1`、`gemini-omni-1.2-flash`、`deep-research-preview-04-2026`）；同任务续写直接复用原 `tabId`。
     - **无弹窗上传本地设定 / 资料（支持 `.md` / `.txt` / `.pdf` / `.docx` / 图片 / 音视频）**：
       1. 若要保留全局长设定（如小说世界观、项目规范），优先点击 `.system-instructions-card` 写入 **System Instructions**；
       2. 需要以**附件芯片**形式传任意本地文件时，用本地命令行将文件读为 Base64，在目标 Tab 通过 `javascript_eval` 构造 `new File([bytes], filename, { type })` 放入 `DataTransfer`，赋给 `ms-add-media-button input[type="file"], input.file-input` 的 `.files` 并派发 `new Event('change', { bubbles: true })`，等待输入区出现文件名且 `Loading...` 消失（显示 `X tokens`）即可（也可直接在开启 CDP 9222 时调 `gemini_web.py attach --file ...`）。
     - **输入与发送**：使用原生 setter + `InputEvent` 写入 `textarea[aria-label="Enter a prompt"]`，等待 `250ms` 后点击非 `.rerun-button` 的 `Run` 按钮。
     - **重要（虚拟滚动懒渲染）**：完成信号为 `.cdk-live-announcer-element` 出现 `"Response ready."`；提取内容前**务必先 `tab_activate(tabId)` 并 `turns[turns.length-1].scrollIntoView()`**！
     - 提取产物：文本读 `[data-turn-role="Model"] ms-cmark-node`（取最后一个非空节点）；图片读 `ms-chat-turn img[src^="blob:"]`（过滤 `naturalWidth > 200` 避开水印小图）及 `button[aria-label="Download"]`；视频读 `<ms-video-generation-gallery> video[src^="blob:"]` 及 `button[aria-label="Download video"]`（可直接浏览器上下文 `fetch(blobUrl)` 转 base64 落盘）。
   - **音乐生成工作台（`/new_music?model=lyria-3.5`）**：
     - 若处于零状态页先点击 `button.empty-state__title-button` 展开编辑区；可切换 `Text` / `Composer` 模式；向 `textarea[aria-label="Prompt input"]` 注入提示词，**等待 `250ms` 待按钮解除 disabled** 后点击 `button.ctrl-enter-submits`（`Generate`）。
     - 生成中显示 `Stop composing`；完成后挂载 `<audio src="data:audio/mpeg;base64,...">` 与 `button.download-button[aria-label="Download"]`，解码 base64 直接写 `.mp3` 文件。
   - **语音合成配音工作台（`/generate-speech?model=gemini-3.8-flash-tts`）**：
     - 零状态页点击 `mat-card.create-dialog-card`（`Create new dialog`）；可用 `button.voice-chip` 选音色/多说话人；向 `textarea[aria-label="Speech block text"]` 写入文本，**等待 `250ms`** 后点击 `button.ctrl-enter-submits`（`Run`）。
     - 完成后挂载 `<audio src="data:audio/wav;base64,...">` 与 `button.download-button[aria-label="Download"]`，解码 base64 直接写 `.wav` 文件。
   - **Build 整站生成与导出（`/apps`）**：
     - 选模式（`Default` / `Plan` / `Max`）与 `settings` 内模型/框架（`React` / `Next.js` / `Angular` / `Android`），向 `div[aria-label="Describe an app and let Gemini do the rest"]` 注入需求点 `button[aria-label="Send"]`；完成后在 `?showCode=true&showAssistant=true` 点 `button[aria-label="Export options"]` 选择 **`Export to Antigravity`** / **`Download as .zip file`** / **`Push to GitHub`**。

2. **`flow.google.com`（生图 0 点数 / 生视频独立点数）**：
   - 打开 `https://flow.google.com/` 点击 `新建项目`（或复用 `/project/<id>`），关掉右侧助手栏或点灭底栏 `智能体` 开关切回直出模式，点 `button[aria-label="设置触发器"]`：选 `image 图片` / `videocam 视频`、比例、模型（`Nano Banana 2.1` / `Omni 1.2 Flash` / `Veo 3.1 - Lite`）、分辨率（`360p` / `720p`）并将数量改为 **`x1`**。
   - 向 `div.ProseMirror[aria-label="您希望创作什么？"]` 填词并点 `button[aria-label="开始生成"]`；完成后在 `.tile-row` 点 `button[aria-label="更多选项"]` 悬停 `下载` 选 `1K 原始尺寸` 或 `2K 已高清重塑`（或取 `flow-content.google` 链接下载）。

3. **`gemini.google.com/app`（对话 / `任务` 异步 Agent / 工具）**：
   - 同任务多轮续聊同样先通过 `tabs_context` 查找并复用已有 `/app/<id>` 标签页。
   - 切 `<gem-segmented-button>`（`对话` / `任务`）及 `bard-mode-menu-button`（`4 Hydrogen` / `4 Argon`），按需选 `上传和工具`（`制作音乐` / `Canvas` / `Deep Research` / 兜底 `制作图片` / `制作视频`）。
   - **本地资料注意**：实测 `gemini.google.com` 会拦截合成 JS `DataTransfer` 上传。在通道 A 中，纯文本/设定集请直接由本地 AI 读取全文并写入 `div[role="textbox"]` 发送；若需上传 PDF / Word / 图片等二进制附件，请优先切到 **AI Studio**（支持 JS `DataTransfer` 无弹窗上传）或调用 **通道 B `gemini_web.py --file`**（Playwright FileChooser 协议层直传）。
   - **禁止设 `innerHTML`**（`TrustedHTML` CSP），用 `textContent` + `InputEvent('insertText')` 注入后点 `button[aria-label="发送"]`。

4. **收尾**：调用 `agentlimb:say` 释放面板状态。

#### 通道 B（CLI 备用）：Playwright CDP 脚本（支持三站全模态 + 无弹窗 `--file` 直传 + 自动落盘）
> `ask` 与 `playground` 默认**优先复用已有同类会话标签页**（并按站点记住上次活跃会话 URL 支持跨重启重连）；需要强制开全新对话时传入 `--new-chat`。
```powershell
$skillDir = "$env:USERPROFILE\.gemini\config\skills\gemini-web-agent" # 或你的本地仓库路径
$py = "$skillDir\.venv\Scripts\python.exe"
$cli = "$skillDir\scripts\gemini_web.py"

# 1. 多端实时额度查询
& $py $cli usage --include-flow
& $py $cli flow-usage

# 2. Google Flow（首选 0 点数 2K 生图 / 独立点数生视频）
& $py $cli flow --media image --model "Nano Banana 2.1" --aspect 16:9 --count 1 --resolution 2K --prompt "提示词" --download-dir "C:\path\to\out"
& $py $cli flow --media video --model "Omni 1.2 Flash" --aspect 16:9 --resolution 720p --count 1 --prompt "提示词" --download-dir "C:\path\to\out"

# 3. AI Studio Playground 全能直达（默认复用同窗口长任务；带 --system-file / --file 无弹窗传入设定；开新对话传 --new-chat）
& $py $cli playground --model hydrogen --system-file "世界观设定.md" --file "人物小传.pdf" --prompt "写出第1章大纲" --new-chat --raw
& $py $cli playground --model hydrogen --prompt "基于第1章大纲继续写正文" --raw   # 自动复用同一窗口/会话
& $py $cli playground --model research --prompt "深度调研主题" --new-chat --raw
& $py $cli playground --model nano2.1 --prompt "watercolor illustration of a cozy lantern" --download-dir "C:\path\to\out"
& $py $cli playground --model omni1.2 --prompt "raindrops glowing on a warm bakery window at night" --download-dir "C:\path\to\out"
& $py $cli playground --model lyria --prompt "warm cozy solo piano and rain ambience, 100bpm" --download-dir "C:\path\to\out"
& $py $cli playground --model tts --prompt "欢迎来到雨夜面包店，今晚外面的雨下得好大呀。" --download-dir "C:\path\to\out"

# 4. 仅无弹窗挂载附件到已有标签页（也可配合通道 A 使用）
& $py $cli attach --site aistudio --file "参考设定.pdf" --tab-hint "https://aistudio.google.com/prompts/..."

# 5. AI Studio Build & Gemini 网页端对话/异步任务（同样支持 --file / --new-chat / --tab-hint）
& $py $cli build --mode default --model hydrogen --framework React --prompt "需求" --download-dir "C:\path\to\out" --extract
& $py $cli ask --entry task --model hydrogen --file "需求文档.pdf" --prompt "异步任务提示词" --async-send
```

### 4. 本地落地与验证
把回传文本、解压后的 Build 工程或下载的 MP3 / WAV / PNG / MP4 落盘本地并验证可用；网格拼图切图用 [slice_sprites.py](scripts/slice_sprites.py)。
