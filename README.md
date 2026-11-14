# Gemini Web-Agent Skill

> **A multi-site, multi-modal quota orchestration Skill for Antigravity & Gemini-based agents.**  
> 专为 **Google AI Pro / Gemini Pro** 与 **Antigravity** 用户打造的**三站点全模态免费额度调度 Skill**：优先通过 **AgentLimb MCP**（永久免弹窗操控已登录外部 Chrome），或备用 **Playwright CDP CLI 脚本**，统筹调度 **`aistudio.google.com`**、**`flow.google.com`** 与 **`gemini.google.com`**，最大化节省本地 5 小时与周配额。

---

## 核心特性 / Highlights

1. **三站点免费与独立配额池统筹**
   - **`aistudio.google.com`（Playground & Build，`key_off` 网页免费额度）**
     - 文本推理 / 长代码与 1M 长输出：`4 Hydrogen`（快、轻耗） / `4 Argon`（深度规划） / `Deep Research`（带 Search + URL context）
     - 视觉生图 / 改图：`Nano Banana 2.1`（`gemini-nano-banana-2.1`）
     - 视频生成：`Omni 1.2 Flash` / `Omni 1.1 Flash`
     - 完整歌曲生成：`Lyria 3.5`（直接导出完整 MP3）
     - 语音合成与多角色配音：`Gemini 3.8 Flash TTS`（直接导出 WAV）
     - 整站前端工程生成与导出：`AI Studio Build`（支持 React / Next.js / Angular / Android，可下载 ZIP / Push to GitHub）
   - **`flow.google.com`（Google Flow 独立点数池）**
     - `Nano Banana 2.1` 生图：**0 点数消耗**，支持直接下载 `1K 原始尺寸` 或 `2K 已高清重塑`
     - `Omni 1.2 Flash` / `Veo 3.1 - Lite` 生视频：使用独立每月 Flow 点数池，不消耗本地 coding 配额
   - **`gemini.google.com/app`（Pro 网页主配额 + 异步 Task）**
     - 支持对话模式与异步 `任务 (Task)` 模式、Canvas、制作音乐与 Deep Research
2. **双通道执行架构**
   - **通道 A（首选）：AgentLimb MCP** — 复用你已登录的外部 Chrome（跨重启永久免弹窗授权，直接 DOM/JS 注入与 Blob/Base64 产物落盘）。
   - **通道 B（备用）：Playwright CDP CLI（[`scripts/gemini_web.py`](scripts/gemini_web.py)）** — 通过 Chrome DevTools 调试端口执行多端用量巡检、对话、异步任务、生图、生视频、作曲、TTS 与 Build 工程导出。
3. **先查后用，额度感知调度**
   - 激活后支持巡检 `gemini.google.com/usage` 与 `flow.google.com` 独立点数余额，避免盲目撞限流。
4. **内置精灵图切分工具（[`scripts/slice_sprites.py`](scripts/slice_sprites.py)）**
   - 将 AI 生成的网格拼图 / 精灵表按行列或自动透明包围盒切分为独立 PNG 素材。

---

## 目录结构 / Repository Structure

```text
gemini-web-agent/
├── SKILL.md                  # Agent 技能核心定义与三站点调度/DOM 规范
├── references/
│   └── agentlimb.md          # AgentLimb MCP 日常调用要点备忘
├── scripts/
│   ├── gemini_web.py         # Playwright CDP 备用全功能 CLI 脚本
│   └── slice_sprites.py      # 游戏/UI 精灵拼图自动切图工具
├── requirements.txt          # Python 依赖（playwright, Pillow）
└── README.md
```

---

## 快速安装 / Quick Start

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

### 2. 配置依赖（用于通道 B 备用 CLI 与切图脚本）

```powershell
cd "$env:USERPROFILE\.gemini\config\skills\gemini-web-agent"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> 若使用首选 **通道 A（AgentLimb MCP）**，请确保已在 Chrome 中启用 AgentLimb 扩展并在 `~/.gemini/config/mcp_config.json` 中完成 `agentlimb` MCP 服务配置（详情参见 [`references/agentlimb.md`](references/agentlimb.md)）。

---

## 命令行示例 / CLI Usage (`scripts/gemini_web.py`)

确保你的外部 Chrome 已开启调试端口（或启动 `daemon` 桥接），即可直接通过命令行调用三站点能力：

```powershell
$py = ".\.venv\Scripts\python.exe"
$cli = ".\scripts\gemini_web.py"

# 1. 多端实时额度巡检（Gemini 网页主额度 + Google Flow 独立点数）
& $py $cli usage --include-flow
& $py $cli flow-usage

# 2. Google Flow：0 点数 Nano Banana 2.1 生图并下载 2K 高清 / 独立点数生视频
& $py $cli flow --media image --model "Nano Banana 2.1" --aspect 16:9 --count 1 --resolution 2K --prompt "a glowing cyberpunk energy core" --download-dir "./out"
& $py $cli flow --media video --model "Omni 1.2 Flash" --aspect 16:9 --resolution 720p --count 1 --prompt "neon light particles flowing" --download-dir "./out"

# 3. AI Studio Playground 全模态直达（免 API Key 免费额度）
& $py $cli playground --model hydrogen --prompt "总结以下架构设计方案..." --raw
& $py $cli playground --model research --prompt "Deep research topic" --raw
& $py $cli playground --model nano2.1 --prompt "cozy watercolor lantern" --download-dir "./out"
& $py $cli playground --model omni1.2 --prompt "raindrops glowing on a bakery window" --download-dir "./out"
& $py $cli playground --model lyria --prompt "inspiring synthwave background music, 118bpm" --download-dir "./out"
& $py $cli playground --model tts --prompt "欢迎使用 Gemini Web-Agent 调度三端免费额度！" --download-dir "./out"

# 4. AI Studio Build 整站生成并解压 + Gemini 网页异步任务
& $py $cli build --mode default --model hydrogen --framework React --prompt "一个极简番茄钟网页应用" --download-dir "./out" --extract
& $py $cli ask --entry task --model hydrogen --prompt "异步调研任务..." --async-send
& $py $cli fetch --raw
```

---

## 隐私与安全说明 / Privacy & Security

- 本 Skill **不收集、不上传任何账号凭证**，所有网页交互均在你本地已登录的 Google Chrome 会话中完成。
- 仓库内已移除所有个人本地路径与环境依赖；请勿将你自己的 Cookie、会话目录或下载媒体提交至版本控制。

## License

MIT
