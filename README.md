# Gemini Web-Agent Skill

> **A multi-site, multi-modal quota orchestration Skill for Antigravity & Gemini-based agents.**  
> 专为 **Google AI Pro（含 Jio / Pixel 权益等）** 与 **Antigravity** 用户打造的**三站点全模态免费额度调度 Skill**：默认以 **通道 A（AgentLimb MCP）** 直接复用日常 Chrome 已登录账号作为零风险托底；对追求极致多标签页并发提速的进阶用户，可自主选择开启 **通道 B（独立 AI Chrome Profile + `daemon` + `wave` 并发引擎）**，统筹调度 **`aistudio.google.com`**、**`flow.google.com`** 与 **`gemini.google.com`**。
>
> **特别针对 Jio 会员 / 部分 Pro 账号**：当你的本地 Antigravity 客户端只给了 `3.8 Flash`、用不到 **`4 Neon` / `4 Hydrogen` / `4 Argon`**，或者本地 5 小时/周配额提前见底时，可用本 Skill 让本地 AI **通过网页端“曲线救国”直接调用满血 `4 Neon`、`4 Hydrogen` 与 `4 Argon`**，顺便分流生图、视频、作曲、配音与整站 Build 源码导出。

> **多客户端通用**：不仅支持 **Antigravity / Gemini CLI**，同样支持 **Claude Code / Codex / Cursor**——将深度推理、1M 长文档调研、前端原型 Build、生图/生视频/作曲/配音等高耗配额任务分流至外部浏览器免费额度池，从而大幅节省你本地 Claude / Codex / Antigravity 的 5 小时滚窗或 API Token。

---

## 🤖 让你的 AI 一键自动配置 / Zero-Touch Setup for AI Agents

只要你电脑上的 AI Agent（**Antigravity / Gemini CLI / Claude Code / Cursor / Codex**）能访问网络或本地终端，**直接把下面这句话发给你的 AI，它就会自动帮你拉取并配好全部环境**：

```text
请帮我拉取并自动配置这个 Skill：https://github.com/582835293/gemini-web-agent
（克隆后运行 python scripts/setup_skill.py --auto，并按输出的状态结果检查浏览器通道）
```

你也可以手动执行两条命令完成零配置初始化，或一键检查/升级 Skill 到最新版：
```bash
git clone https://github.com/582835293/gemini-web-agent.git
cd gemini-web-agent && python scripts/setup_skill.py --auto

# 自动检查 GitHub 更新与一键自动升级同步：
python scripts/setup_skill.py --check-update
python scripts/setup_skill.py --update
```
`setup_skill.py` 会自动完成：① 同步 Skill 至全球目录（如 `~/.gemini/config/skills/gemini-web-agent`）并写入版本校验元数据 `.skill_version.json`；② 创建独立 `.venv` 并安装 `playwright`（不下载 300MB 冗余浏览器）；③ 自动探测本机 **AgentLimb MCP** 与 **Chrome 调试端口** 状态并输出精简行摘要（加 `--json` 可看完整结构）；④ 支持 `--check-if-stale`（24h 缓存零延迟）与 `--update`（自动 `git pull` 或 GitHub ZIP 兜底同步升级）。

---

## 核心特性 / Highlights

1. **「双模自适应总监 + 虚拟公司一页一员工」多标签协作架构（兼顾强弱本地模型极致省流）**
   - **重活统一外包，本地绝不硬扛**：无论是高级模型还是轻量模型，大段代码生成、万字综述与素材批处理一律外包给外部 Chrome 员工 Tab（1 Tab = 1 名持久化员工），本地只走 `--out-file` / Python `zipfile` / `harvest` 落盘并跑测试把 stderr 回传返工。
   - **双模分流“谁当总监”**：**本地已是高级模型（`4 Neon` / `Argon` / Claude Opus / Codex）**可直接挂帅当总监、跳过外部总监往返直派多路员工 Tab 干重活，把昂贵的本地 5h 高级额度 100% 留给架构拍板与验收；**本地是轻量/受限模型**则连架构规划权一并交由 [`references/director_prompt.md`](references/director_prompt.md)（Playground `4 Neon` 总监）拆单，本地纯做传话与文件总线。
   - **三阶段用户互动拍板机制**：不替用户擅自拿主意——**开局问需求与模式/渠道选择** → **总监出炉《花名册》后经用户会审才批量开 Tab** → **Wave 阶段产出先过目验收、新增编队先征求同意再 `playbook add` 落盘**。
   - **主流通用编队 + AI 自主扩展**：内置 [`references/playbooks/`](references/playbooks/) 下的 5 套大众主流工作编队（全栈 Web/SaaS、数据报表与办公自动化、自媒体短视频与播客、深度调研与学术写作、互动游戏与创意工作室），且支持经用户同意后通过 `gemini_web.py playbook add` 沉淀新增领域编队、通过 `roster` 维护工程根目录 `.web-team.json` 员工花名册。
2. **四大站点精准分工与思考等级调速**
   - **`aistudio.google.com`（Playground `key_off` 免费纯文本大脑 & 音频台）**
     - 纯文本推理 / 长代码与 1M 长输出：`4 Neon`（最新旗舰）/ `4 Hydrogen`（快、轻耗）/ `4 Argon`（深度规划）/ `Deep Research`（带 Search + URL context），支持按任务快慢动态调整思考等级（`--thinking-level minimal/low/medium/high/extra_high`），并拉满最大输出上限（`1,048,576`）
     - 完整歌曲生成：`Lyria 3.5`（直接导出完整 MP3）
     - 语音合成与多角色配音：`Gemini 3.8 Flash TTS`（直接导出 WAV）
     - 视频生成：`Omni 1.2 Flash` / `Omni 1.1 Flash`（`key_off` 免费不耗 Flow 点数）与视觉生图兜底：`Nano Banana 2.1`
   - **`gemini.google.com/app`（专注 `任务 (Task)` 异步实战员工）**
     - 专攻 **`任务 (Task)`** 模式：自带跨轮持久化的 **`Debian 12` (2C / 7.8G / 19G) 云端断网沙盒**（预装 `python3 3.11` / `node 18` / `gcc 12` / `ffmpeg 5.1` / `libreoffice 7.4` / 无头 `chromium 156` / `PIL` / `cv2` / `pydub` / `pandas` / `matplotlib`），重活/主程/QA 用 **`4 Neon`**，素材批处理/切图/混音/清洗脚本用 **`4 Hydrogen`**（要求统一用 Python `zipfile` 打包交付）
   - **`aistudio.google.com/apps`（Build 整包外包团队）**
     - 适合从零构建完整整套 Web 应用（`MAX` + `4 Neon` 导出 `.zip`），支持内嵌防擅自加料负面契约
   - **`flow.google.com`（Google Flow 独立点数池 — 视觉素材工厂）**
     - `Nano Banana 2.1` 生图：**0 点数消耗（每日有数十张免费限额，默认按 `x1` 生成省着用）**，支持直接下载 `1K 原始尺寸` 或 `2K 已高清重塑`；产出原图可直接转交 Gemini `Task` 做自动化抠图切图后期
   - **`Omni 1.2 Flash` / `Veo 3.1 - Lite` 生视频**：使用独立每月 Flow 点数池，不消耗本地 coding 配额
3. **安全透明的双通道自由选择架构（托底保稳 + 并发可选）+ 云端共享总线**
   - **选项 1（默认托底首选）：通道 A — AgentLimb MCP（复用日常 Chrome，无需重新登录）**
     直接复用你日常 Chrome 中已登录的所有 Google 账号，**不需要新建目录、不需要重新输入账号密码**，对最在意账号安全与零折腾的用户最友好（推荐安装 `AgentLimb >= v0.8.2`）。适合中轻度任务，但在多员工多波次并发场景下因需逐轮工具调用，耗时相对较长。
   - **选项 2（进阶提速 5~10 倍）：通道 B — 独立 AI Chrome Profile + `daemon` + `wave` 一键并发引擎（完全由用户自己决定是否启用）**
     - 为何需要单独建一个 Chrome Profile？因为 Chrome 136+ 已在内核禁止对日常默认 `User Data` 目录通过参数开启永久 CDP 调试端口。
     - **完全本地、透明、绝不碰日常账号**：如果你希望体验 `gemini_web.py wave --spec wave1.json` **单条命令并发起跑 4~8 个 Tab、提速 5~10 倍并省去 80%+ 本地推理往返**，可由你自己决定运行 `python scripts/setup_skill.py --setup-ai-chrome --launch-ai-chrome`（或在日常 Chrome 地址栏访问 `chrome://inspect/#remote-debugging` 手动点允许）。独立 Profile（`~/.gemini-web-chrome`，端口 `9229`）的所有 Cookie/会话数据**100% 保存在你本机桌面目录内、开源代码完全可审计、绝不上传任何账号凭证**——只是首次打开时需要你在新窗口里自行登录一次 Google 账号。
   - **Google Drive 云端总线 & Gemini Web `Import code`**：AI Studio 对话默认存入同账号 Google Drive（传 `--title` 命名并自动提取 `drive_file_id`），下游 Gemini `Task` 员工可直接从 Drive 拉取上游架构/源码零中转；同时支持 `ask --folder "./src"` 与 `ask --github "https://github.com/..."` 通过 `More uploads -> Import code` 一键导入本地代码文件夹或 GitHub 仓库。
3. **先查后用，额度感知调度（内置 Antigravity 本地双轨与路由检测）**
   - 激活后支持巡检 `gemini.google.com/usage` 与 `flow.google.com` 独立点数余额，并**内置 [`scripts/inspect_antigravity.py`](scripts/inspect_antigravity.py)**（纯标准库零依赖，可探测本地 Antigravity Connect-RPC 双轨配额、SQLite `gen_metadata` 后端实际路由与四维 Token 消耗；Claude Code / Codex 等客户端自动跳过本地对比，直接分流省额度）。

> 📺 **B 站实战讲解视频**：https://www.bilibili.com/video/BV1cZsV6MEVb （含零配置部署演示、多模态素材流水线与真实额度消耗对比）

---

## 目录结构 / Repository Structure

```text
gemini-web-agent/
├── SKILL.md                  # Agent 核心规范（纯调度接口定位 + 多员工编队调度协议）
├── references/
│   ├── agentlimb.md          # AgentLimb MCP 日常备忘、防冻结落盘与参考图连招
│   ├── director_prompt.md    # 外部 4 Neon 总监招工元提示词与结构化派单协议
│   ├── models.md             # AI Studio & Google Flow 全分类模型速查表
│   └── playbooks/            # 5 套大众主流行业编队卡（支持 AI 自主新增扩展）
│       ├── web_fullstack_app.md
│       ├── data_office_automation.md
│       ├── content_video_media.md
│       ├── academic_deep_research.md
│       └── interactive_game_studio.md
├── scripts/
│   ├── setup_skill.py        # AI 一键自动安装、建 .venv 与跨平台通道自检脚本
│   ├── platform_utils.py     # 跨发行版 Linux /proc 与 Win32 探测、venv 兜底与 Chromium 注册表
│   ├── gemini_web.py         # Playwright CDP 全功能 CLI + roster/playbook/harvest 编队工具
│   └── inspect_antigravity.py # 内置 Antigravity 本地双轨配额、后端路由与 Token 消耗检测脚本
├── tests/
│   ├── test_core.py          # 纯标准库离线冒烟测试（模型/编队/花名册/harvest/跨发行版与/proc）
│   └── test_perf_and_dom.py  # inspect 耗时基准测试与 Node DOM 状态机测试
├── requirements.txt          # Python 依赖（playwright）
└── README.md
```

---

## 手动配置详情 / Manual Setup (Optional)

> 如已运行上方 `python scripts/setup_skill.py --auto`，以下手动步骤可全部跳过。

### 1. 安装 Skill 到本地 Agent 目录

将本仓库克隆到你的 Antigravity（或兼容 Agent Skills 规范的工具）全局技能目录：

**Windows (PowerShell):**
```powershell
git clone https://github.com/582835293/gemini-web-agent.git "$env:USERPROFILE\.gemini\config\skills\gemini-web-agent"
```

**macOS / Linux:**
```bash
git clone https://github.com/582835293/gemini-web-agent.git ~/.gemini/config/skills/gemini-web-agent
```

### 2. 配置依赖（用于通道 B 备用 CLI）

```powershell
cd "$env:USERPROFILE\.gemini\config\skills\gemini-web-agent"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> 若使用首选 **通道 A（AgentLimb MCP）**，推荐安装 **`AgentLimb >= v0.8.2`**（修复了本地 `8765` 端口冲突时的内存泄漏问题），请确保已在 Chrome 中启用 AgentLimb 扩展并在对应客户端完成 `agentlimb` MCP 服务配置（排查提示与细节参见 [`references/agentlimb.md`](references/agentlimb.md)）。

---

## 命令行示例 / CLI Usage (`scripts/gemini_web.py`)

确保你的外部 Chrome 已开启调试端口（或启动 `daemon` 桥接），即可直接通过命令行调用三站点能力：

```powershell
$py = ".\.venv\Scripts\python.exe"
$cli = ".\scripts\gemini_web.py"

# 0. 一键创建并启动专用独立 AI Chrome（首次登录一次后永久免弹窗，自动解锁高速通道 B）
python .\scripts\setup_skill.py --setup-ai-chrome --launch-ai-chrome
Start-Process -WindowStyle Hidden $py "$cli daemon"

# 1. 一键并发波次调度（核心提速：1 条命令同时驱动多个独立 Tab，自动解包/下载并回写花名册）
& $py $cli wave --spec ".\proj\wave1.json" --roster-file ".\proj\.web-team.json" --project-dir ".\proj" --timeout 360
python $cli roster audit --file ".\proj\.web-team.json" --project-dir ".\proj" --min-roles 2

# 2. 多端实时额度巡检（默认均输出极简行摘要省 Token；完整版可加 --json / --markdown）
& $py $cli usage --include-flow
& $py $cli flow-usage
python .\scripts\inspect_antigravity.py   # 仅 Antigravity 环境按需对比本地 5h/周配额与路由

# 3. Google Flow：0 点数 Nano Banana 2.1 生图并下载 2K 高清 / 独立点数生视频
& $py $cli flow --role artist --media image --model "Nano Banana 2.1" --aspect 16:9 --count 1 --resolution 2K --prompt "a glowing cyberpunk energy core" --download-dir "./out"
& $py $cli flow --media video --model "Omni 1.2 Flash" --aspect 16:9 --resolution 720p --count 1 --prompt "neon light particles flowing" --download-dir "./out"

# 4. AI Studio Playground 全模态直达（支持 --role / --title 同步 Drive / --unpack-json-dir 自动解包 / --file 无弹窗上传）
& $py $cli playground --role coder --title "[MyApp] coder" --model neon --thinking-level high --system-file "./世界观设定.md" --file "./人物小传.pdf" --prompt-file "./task.txt" --unpack-json-dir "./proj" --new-chat
& $py $cli playground --model research --prompt "Deep research topic" --new-chat --raw
& $py $cli playground --model lyria --prompt "inspiring synthwave background music, 118bpm" --download-dir "./out"
& $py $cli playground --model tts --prompt "欢迎使用 Gemini Web-Agent 调度三端免费额度！" --download-dir "./out"

# 5. Gemini Web Task（支持 --folder 导入本地代码目录、--github 导入 GitHub 仓库、或直接读 Google Drive）+ Build + 归档
& $py $cli ask --role qa_tester --model neon --folder "./proj" --prompt "在沙盒自测并输出 patch" --out-file "./qa.md"
& $py $cli ask --model hydrogen --github "https://github.com/582835293/gemini-web-agent" --prompt "分析仓库架构" --out-file "./review.md"
& $py $cli build --mode max --model neon --framework React --prompt "一整套完整全栈/多页应用需求" --download-dir "./out" --extract
& $py $cli harvest --pattern "bundle*.json" --unpack-json --dest "./out"
```

---

## 社区生态与衍生项目 / Community Ecosystem

- **[dsh-gemini-web](https://github.com/stJL/dsh-gemini-web)**（by [@stJL](https://github.com/stJL)）：基于本项目的 **DeepSeek Harness (DSH)** 桌面插件，提供了可视化 GUI 设置仪表盘、Python 直连 AgentLimb RPC、确定性「先问后用」确认卡、多阶模型降级梯队以及网格拼图切图工具。

---

## 隐私与安全说明 / Privacy & Security

- 本 Skill **不收集、不上传任何账号凭证**，所有网页交互均在你本地已登录的 Google Chrome 会话中完成。
- 仓库内已移除所有个人本地路径与环境依赖；请勿将你自己的 Cookie、会话目录或下载媒体提交至版本控制。

## License

MIT
