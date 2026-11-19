# Gemini Web-Agent Skill

> **A multi-site, multi-modal quota orchestration Skill for Antigravity & Gemini-based agents.**  
> 专为 **Google AI Pro（含 Jio / Pixel 权益等）** 与 **Antigravity** 用户打造的**三站点全模态免费额度调度 Skill**：优先通过 **AgentLimb MCP**（永久免弹窗操控已登录外部 Chrome），或备用 **Playwright CDP CLI 脚本**，统筹调度 **`aistudio.google.com`**、**`flow.google.com`** 与 **`gemini.google.com`**。
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

1. **三站点免费与独立配额池统筹**
   - **`aistudio.google.com`（Playground & Build，`key_off` 网页免费额度）**
     - 文本推理 / 长代码与 1M 长输出：`4 Neon`（最新旗舰）/ `4 Hydrogen`（快、轻耗）/ `4 Argon`（深度规划）/ `Deep Research`（带 Search + URL context），默认自动拉到最高可用思考等级（如 `Extra High`）与最大输出上限（`1,048,576`）
     - 视觉生图 / 改图：`Nano Banana 2.1`（`gemini-nano-banana-2.1`，Flow 日限用完后接力兜底）
     - 视频生成：`Omni 1.2 Flash` / `Omni 1.1 Flash`
     - 完整歌曲生成：`Lyria 3.5`（直接导出完整 MP3）
     - 语音合成与多角色配音：`Gemini 3.8 Flash TTS`（直接导出 WAV）
     - 整套全栈工程生成与导出：`AI Studio Build`（适合从零构建完整整套项目，默认调至最高可用 `MAX` + `4 Neon`；简单任务勿用 Build）
   - **`flow.google.com`（Google Flow 独立点数池）**
     - `Nano Banana 2.1` 生图：**0 点数消耗（每日有数十张免费限额，默认按 `x1` 生成省着用）**，支持直接下载 `1K 原始尺寸` 或 `2K 已高清重塑`
     - `Omni 1.2 Flash` / `Veo 3.1 - Lite` 生视频：使用独立每月 Flow 点数池，不消耗本地 coding 配额
   - **`gemini.google.com/app`（Pro 网页主配额 + 异步 Task，高优先级）**
     - 支持对话模式与高优 **`任务 (Task)` 异步 Agent 模式**（`4 Hydrogen` 产出干净不乱加脚手架，简单/中等开发与调研任务优先级高于 AI Studio Build）、**`4 Neon`**（已取代网页端 `4 Argon`）、Canvas、制作音乐与 Deep Research
2. **双通道执行架构（支持长任务复用与无弹窗上传本地设定）**
   - **通道 A（最稳首选）：AgentLimb MCP** — 复用你已登录的外部 Chrome（跨重启永久免弹窗授权，不改浏览器启动参数、不强杀进程、不掉已登录账号与扩展）；支持在同一个会话标签页连续续聊写长文/改代码，并支持在 AI Studio 通过 `DataTransfer` 无弹窗自动上传本地 `.md` / `.txt` / `.pdf` / 图片等资料。
   - **通道 B（备用）：Playwright CDP CLI（[`scripts/gemini_web.py`](scripts/gemini_web.py)）** — 在 Chrome 地址栏开启 `chrome://inspect/#remote-debugging`（或独立隔离工作目录）后配合 `daemon` 使用，支持多端用量巡检、对话、异步任务、生图、生视频、作曲、TTS 与 Build 工程导出；支持 **`--file` / `--system-file` / `attach`** 无弹窗直传本地文件，且默认复用当前同类会话窗口（开新对话传 `--new-chat`）。*(注：Chrome 136+ 已禁止对默认 `User Data` 使用 `--remote-debugging-port=9222`，日常主力多账号环境强烈建议直接用通道 A)*。
3. **先查后用，额度感知调度（内置 Antigravity 本地双轨与路由检测）**
   - 激活后支持巡检 `gemini.google.com/usage` 与 `flow.google.com` 独立点数余额，并**内置 [`scripts/inspect_antigravity.py`](scripts/inspect_antigravity.py)**（纯标准库零依赖，可探测本地 Antigravity Connect-RPC 双轨配额、SQLite `gen_metadata` 后端实际路由与四维 Token 消耗；Claude Code / Codex 等客户端自动跳过本地对比，直接分流省额度）。

> 📺 **B 站实战讲解视频**：https://www.bilibili.com/video/BV1cZsV6MEVb （含零配置部署演示、多模态素材流水线与真实额度消耗对比）

---

## 目录结构 / Repository Structure

```text
gemini-web-agent/
├── SKILL.md                  # Agent 技能核心定义与自动部署/三站点调度规范
├── references/
│   ├── agentlimb.md          # AgentLimb MCP 日常备忘、防冻结落盘与参考图连招
│   └── models.md             # AI Studio & Google Flow 全分类模型速查表
├── scripts/
│   ├── setup_skill.py        # AI 一键自动安装、建 .venv 与跨平台通道自检脚本
│   ├── platform_utils.py     # 跨发行版 Linux /proc 端口探测、venv 兜底与 Chromium 家族注册表
│   ├── gemini_web.py         # Playwright CDP 备用全功能 CLI + 下载归档工具
│   └── inspect_antigravity.py # 内置 Antigravity 本地双轨配额、后端路由与 Token 消耗检测脚本
├── tests/
│   ├── test_core.py          # 纯标准库离线冒烟测试（模型/行协议/harvest/跨发行版与/proc）
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

# 1. 多端实时额度巡检（默认均输出极简行摘要省 Token；完整版可加 --json / --markdown）
& $py $cli usage --include-flow
& $py $cli flow-usage
python .\scripts\inspect_antigravity.py   # 仅 Antigravity 环境按需对比本地 5h/周配额与路由

# 2. Google Flow：0 点数 Nano Banana 2.1 生图并下载 2K 高清 / 独立点数生视频
& $py $cli flow --media image --model "Nano Banana 2.1" --aspect 16:9 --count 1 --resolution 2K --prompt "a glowing cyberpunk energy core" --download-dir "./out"
& $py $cli flow --media video --model "Omni 1.2 Flash" --aspect 16:9 --resolution 720p --count 1 --prompt "neon light particles flowing" --download-dir "./out"

# 3. AI Studio Playground 全模态直达（默认同窗口复用；支持 --system-file / --file 无弹窗上传；开新对话传 --new-chat）
& $py $cli playground --model hydrogen --system-file "./世界观设定.md" --file "./人物小传.pdf" --prompt "列出第1章大纲" --new-chat --raw
& $py $cli playground --model hydrogen --prompt "基于第1章大纲写正文" --raw
& $py $cli playground --model research --prompt "Deep research topic" --new-chat --raw
& $py $cli playground --model nano2.1 --prompt "cozy watercolor lantern" --download-dir "./out"
& $py $cli playground --model omni1.2 --prompt "raindrops glowing on a bakery window" --download-dir "./out"
& $py $cli playground --model lyria --prompt "inspiring synthwave background music, 118bpm" --download-dir "./out"
& $py $cli playground --model tts --prompt "欢迎使用 Gemini Web-Agent 调度三端免费额度！" --download-dir "./out"

# 4. 仅挂载本地文件到已打开标签页 + Gemini 高优异步 Task（默认已切为 task）+ Build + 零上下文归档
& $py $cli attach --site aistudio --file "./补充资料.txt"
& $py $cli ask --model hydrogen --file "./需求说明.pdf" --prompt "异步调研/轻量原型任务..." --async-send
& $py $cli fetch --out-file "./result.md"
& $py $cli build --mode max --model neon --framework React --prompt "一整套完整全栈/多页应用需求" --download-dir "./out" --extract
& $py $cli harvest --pattern "bundle*.json" --unpack-json --dest "./out"
```

---

## 隐私与安全说明 / Privacy & Security

- 本 Skill **不收集、不上传任何账号凭证**，所有网页交互均在你本地已登录的 Google Chrome 会话中完成。
- 仓库内已移除所有个人本地路径与环境依赖；请勿将你自己的 Cookie、会话目录或下载媒体提交至版本控制。

## License

MIT
