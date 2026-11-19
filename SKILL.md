---
name: gemini-web-agent
description: >-
  将本地配额留给核心决策，把海量生成、沙盒研发与多模态重活全部外包给外部 Chrome 员工标签页（默认以 AgentLimb 复用日常 Chrome 为免重登稳妥托底，若用户已启用独立 Profile / CDP 则自动切换高速通道 B `wave` 并发引擎；兼顾双模自适应总监 + Google Drive 云端共享总线 + Import Code + 审计门禁）：
  (1) aistudio.google.com Playground (key_off 免费纯文本大脑：总监/架构/审稿/文案，自动存 Google Drive 供下游 Task 直接拉取；按快慢调 minimal/low/medium/high/extra_high；另有 Lyria 3.5 配乐、3.8 Flash TTS 配音、Omni 1.2 视频、Nano Banana 2.1 生图)；
  (2) gemini.google.com/app 专注 `任务 (Task)`（自带 Debian 12 断网沙盒 + 预装 python3/node/gcc/ffmpeg/libreoffice/chromium/PIL/cv2/pandas/pydub；支持 Google Drive 读取与 More uploads -> Import code 导入本地文件夹/GitHub 仓库）；
  (3) aistudio.google.com/apps Build（整站外包团队：MAX + 4 Neon，必带防擅自加料契约）；
  (4) flow.google.com 独立点数池（Nano Banana 2.1 生图 0 点数 + x1 + 2K）。
  当用户提到“网页端 Gemini”、“Google Flow”、“Flow”、“AI Studio”、“Playground”、“Build模式”、“Lyria”、“TTS配音”、“生图”、“生视频”、“生音乐”、“利用网页版额度”、“省额度”、“任务模式”、“异步 agent”、“多标签页协作/分角色团队”时激活。
---

# Gemini Web-Agent（双模自适应总监 + 托底安全/并发自选 + 防伪造门禁）

> **【防偷懒与防串台四条死令（违者视为任务彻底失败）】**
> 1. **严禁多个角色共用同一个标签页/会话**：通道 B 必须通过 `wave` 或 `--role <role>` 自动分配独立 Tab（CLI 内置 `ROLE_URL_CONFLICT` 拦截）；通道 A 必须对每个新角色调用 `tab_new` + `roster set --tab-id`（CLI `ROLE_TAB_CONFLICT` + JS `window.__WEB_TEAM_ROLE` 双重拦截）。
> 2. **模式 B 下严禁本地 `write_file` 编写业务源码，严禁用 Canvas 几何块或 WebAudio 振荡器伪造替代 Flow/Lyria/TTS 资产**：所有外包代码必须由网页员工产出并经 `wave --unpack-json-dir` 或 `harvest --unpack-json` 落盘；美术/音频必须真实生成下载入 `assets/`（模式 A 本地强模型也严禁手写万字或手抄大产物）。
> 3. **通道选择与用户知情自选 + 防风控节流原则**：先看 `setup_skill.py` 输出——若用户已自备且运行了 `prefer=B`，使用高速通道 B (`gemini_web.py wave` 默认带 `3.5s` 拟人错峰与新页水合停顿，严禁 `--stagger 0` 疯狂连刷防风控)；若仅 `prefer=A`，优先稳妥走 AgentLimb 托底（禁 `read_page`/`form_input`/`computer`，`javascript_eval` 用 `expression`，`wait` 用 `timeout`，每次操作后留自然间隔），**绝不未征得用户同意擅自拉起需重新登录的新 Chrome 窗口！**
> 4. **完工交差前必跑 `roster audit` 门禁**：交付前必须运行 `python scripts/gemini_web.py roster audit --file "<项目>/.web-team.json" --project-dir "<项目>"`，返回 `ok | audit=passed` 方可验收；出现 `MISSING_FLOW_IMAGES` / `MISSING_AUDIO_FILES` / `DUPLICATE_TAB_ID` / `DUPLICATE_SESSION_URL` 必须立刻补齐真实外包！

---

## 0. 自动初始化、通道透明度与安全红线

1. **首次或排查环境运行**（默认返回极简 1 行含 `prefer=B|A`）：
   ```bash
   python scripts/setup_skill.py --auto
   python scripts/setup_skill.py --check-if-stale   # 24h 内 10ms 返回；遇 update=available 经同意跑 --update
   ```
2. **【通道说明与选择权交给用户（防“盗号”误解）】**：
   - **默认免重登托底首选（通道 A：AgentLimb MCP）**：直接复用你正在用的日常 Chrome 已登录账号，无需新建目录、无需重新输入 Google 账号密码，开箱稳妥；适合常规需求，但受浏览器原子通信限制，多波次并发时本地往返次数较多、整体较慢。
   - **高速并发可选方案（通道 B：独立 AI Chrome Profile，`--setup-ai-chrome --launch-ai-chrome`）**：如你想用 `gemini_web.py wave` 单条命令并发跑完多 Tab（提速 5~10 倍、省 80%+ 本地 Token），可**自主选择**在本机新建一个与日常 Chrome 彻底隔离的专用目录（`~/.gemini-web-chrome` + 端口 `9229`）。**需要你本人明确同意后才创建，并在该新窗口自己登录一次 Google 账号**（开源脚本纯本地运行，绝不触碰日常 `User Data`、绝不收集或上传任何账号凭证）。也可在日常 Chrome 地址栏开启 `chrome://inspect/#remote-debugging` 后按弹窗允许免重登直连通道 B。
3. **【绝对红线】严禁 `taskkill` 强杀正在运行的日常 Chrome，严禁篡改或复制默认 `User Data`；严禁未征求用户同意擅自执行 `--setup-ai-chrome --launch-ai-chrome`！**

---

## 一、 双模总监 + 四大部门能力边界 + 云端共享总线

- **模式 A（本地已是高级模型，仅省 5h 额度）**：本地直接挂帅当总监，按编队卡定死契约并经用户确认后直接用 `wave` 并发外包重活，省去外部总监等待。
- **模式 B（本地是 `3.8 Flash` 等轻量/受限模型）**：**连规划与写 Prompt 一起外包**！先用 `--role director` 投喂 [references/director_prompt.md](references/director_prompt.md) 拆出澄清问题与全套工单，禁止本地自己拍脑门写代码。

| 部门渠道 | 定位与分工 | 关键参数 / 能力边界（务必写入工单） |
| :--- | :--- | :--- |
| **AI Studio Playground**<br>(`/prompts/new_chat?model=<id>`, `key_off`) | **纯文本大脑组**（`4 Neon` / 快手 `4 Hydrogen` / `deep-research-preview-04-2026`） | **Thinking Level 调速**：快活 `low`/`medium`；常规研发 `high`；复杂架构 `extra_high`。Output 拉 `1048576`；代码要求输出单个 JSON `{相对路径: 内容}`（通道 B 传 `unpack_json_dir` 自动解包落盘）。**传 `--title "[项目] 角色"` 同步命名到 Google Drive**。 |
| **Gemini Web `任务 (Task)`**<br>(`gemini.google.com/app`, 弃用 Web 聊天) | **带 Linux 电脑的实战员工**（主程/自测用 **`4 Neon`**；后期/清洗用 **`4 Hydrogen`**） | **Debian 12 沙盒（2C / 7.8G / 19G，跨轮持久化）**：预装 `python3 3.11`、`node 18`、`gcc 12`、`git`、`ffmpeg 5.1`、`libreoffice 7.4`、`chromium 156`、`PIL`、`cv2`、`pydub`、`pandas`、`matplotlib`。<br>**硬限制**：① **完全断网**（禁 `pip/npm install`）；② 无 `zip` CLI（须用 **Python `zipfile`** 打包）。 |
| **AI Studio Build** (`/apps`) | **整包外包公司**（仅从零建整站 Web） | 选 `MAX` + `Gemini 4 Neon`，工单必附《防擅自加料契约》锁定文件清单与接口。 |
| **Flow + AI Studio 音频台** | **零成本素材工厂**（再可交 Task 后期） | 生图走 **`flow.google.com`**（`Nano Banana 2.1`，0 点数 `x1`，下 `1K/2K`）；音乐 `/new_music?model=lyria-3.5`；配音 `/generate-speech?model=gemini-3.8-flash-tts`；视频 `gemini-omni-1.2-flash`。 |

### 【两大免中转协作红利（强烈优先利用）】
1. **Google Drive 云端共享总线**：AI Studio 会话会自动保存到同一 Google 账号的 Google Drive（URL `/prompts/<drive_file_id>` 即文件 ID，`--title` 即文件名）。给上游 AI Studio 员工加上 `title`（如 `[MyApp] arch_spec`）后，**下游 Gemini Web `Task` 员工可直接检索 Google Drive 拉取该 JSON 提取源码/文档并做自动化测试或打包**，零本地下载再上传！
2. **Gemini Web `Import code`（本地文件夹 / GitHub 直传）**：需要把整个本地项目或 GitHub 仓库交给 Gemini `Task` 审查、重构或测试时，直接用 `ask --folder "./src"` 或 `ask --github "https://github.com/..."`（或网页端 `Upload & tools -> More uploads -> Import code`），无需逐个传文件。

> **速查**：模型清单见 [references/models.md](references/models.md)；5 套主流编队用 `python scripts/gemini_web.py playbook list/show` 查看（经同意后可 `playbook add` 新增）。

---

## 二、 多端额度感知与三阶段互动拍板

1. **巡检额度**：通道 B 跑 `& $py $cli usage --include-flow`（通道 A 查 `/usage` 与 Flow），Antigravity 环境顺便跑 `python "<inspect路径>"` 对比本地配额。
2. **三阶段必问用户（优先用 `ask_question` / `AskUserQuestion`）**：
   - **节点 1（开局定调）**：结合余额问清需求模糊点（技术栈/风格/交付边界）、确认模式 A/B 及选用编队；**若当前为通道 A 托底，须透明告知用户两选项利弊由其自选：“默认直接用日常 Chrome 托底（免重登、安全稳妥但多 Tab 往返略慢），若想 5~10 倍并发提速可由你同意后配置本地独立 Profile（需在新窗口登录一次）”**。
   - **节点 2（花名册会审）**：展示拟开的员工角色列表、站点与分工，经用户点头后再批量并发点火。
   - **节点 3（波次验收 & 沉淀确认）**：Wave 1 核心产出或主视觉落地后先请用户过目；新增永久编队（`playbook add`）前须征得用户同意。

---

## 三、 高速执行通道（禁止派 `browser` 子代理）

### 通道 B（高速引擎，用户启用独立 Profile / 调试端口后自动选用）

**核心原理**：所有切换、发包、多 Tab 并发等待与文件落盘全在本地 Python/CDP 进程内完成，**本地 AI 只需写 1 个 `waveN.json` 并执行 1 条命令**，即可把原本 400+ 次浏览器微操压缩为 **3~5 次 CLI 调用**！

```powershell
# 0. 仅当用户主动选择提速并同意启用独立 Profile 时执行（首次需用户自己登录一次；日常已有可用通道时跳过）
python $cli/../setup_skill.py --setup-ai-chrome --launch-ai-chrome

# 1. 可选：启动常驻 daemon（自动连用户开启的 AI Chrome 9229，省冷启动，10 分钟空闲自动退）
Start-Process -WindowStyle Hidden $py "$cli daemon"

# 2. 单兵按角色调用（自动从 .web-team.json 绑定独立 Tab，支持 --title / --folder / --github / --unpack-json-dir）
& $py $cli playground --role director --title "[MyApp] director" --model neon --thinking-level high --system-file "references/director_prompt.md" --prompt-file "./brief.txt" --out-file "./docs/plan.md"
& $py $cli ask --role qa_tester --model neon --folder "./proj" --prompt "在 Debian 12 沙盒运行无头 Chromium 测完并输出 patch" --out-file "./docs/qa.md"

# 3. 核武器：单条 wave 命令并发起跑整批员工（自动开独立 Tab -> 并发发射 -> 后台静默等待 -> 自动解包/下载 -> 回写花名册）
& $py $cli wave --spec "./proj/wave1.json" --roster-file "./proj/.web-team.json" --project-dir "./proj" --timeout 360

# 4. 完工审计门禁（退出码 0 方可交差）
python $cli roster audit --file "./proj/.web-team.json" --project-dir "./proj" --min-roles 2
```

**`wave1.json` 极简示例（按需删减，一个对象 = 一个独立员工 Tab）：**
```json
{
  "project": "MyApp",
  "tasks": [
    {"role": "engine_coder", "site": "aistudio", "model": "neon", "thinking_level": "high", "title": "[MyApp] engine_coder", "prompt": "...只输出纯 JSON {相对路径: 内容}", "unpack_json_dir": "."},
    {"role": "sound_bgm", "site": "aistudio", "model": "lyria", "prompt": "dark ambient survival loop, 90bpm", "download_dir": "assets/audio", "save_as": "bgm.mp3"},
    {"role": "concept_artist", "site": "flow", "model": "Nano Banana 2.1", "aspect": "16:9", "count": 1, "prompt": "apocalyptic shelter interior, charcoal style", "download_dir": "assets/images", "save_as": "bg_shelter.png"},
    {"role": "qa_sandbox", "site": "gemini_task", "model": "hydrogen", "folder": ".", "prompt": "也可以从 Google Drive 读取 [MyApp] engine_coder 或检查导入目录，跑测试并汇报", "out_file": "docs/qa_report.md"}
  ]
}
```
> 其余单命令（`usage --include-flow`、`build`、`attach`、`harvest`、`playbook`）均支持 `--help` 查看完整参数。

---

### 通道 A（默认稳妥托底）：AgentLimb MCP — 4 步并发派单流水线

> 直接复用日常 Chrome 已登录账号（无需另建窗口重登，安全透明）；当 `prefer=A` 时直接走本通道，完整四大渠道可复制 JS 宏与精确参数表见 [references/agentlimb.md](references/agentlimb.md)。

1. **批量建房登记**：为每个员工各自 `tab_new` 并跑 `python $cli roster set --role <r> --tab-id <id>`。
2. **并发点火**：连续对 Wave 1 所有角色 Tab 注入带 `window.__WEB_TEAM_ROLE` 锁的发包 JS（**不中途死等，让多 Tab 同时开工**；`javascript_eval` 参数必须用 `expression`，`wait` 参数必须用 `timeout`）。
3. **激活收割落盘**：依次 `wait(condition="page_contains", text="Response ready.", timeout=30000)` → `tab_activate(tabId)` → 触发 `bundle-<role>.json` 或媒体下载 → `python $cli harvest --pattern "bundle-*.json,*.png,*.mp3,*.wav,*.zip" --unpack-json --dest "<项目>"`。
4. **门禁验收 & 收尾**：跑 `roster audit` 通过并完成本地测试后，调用 `agentlimb:say` 释放侧边栏。
