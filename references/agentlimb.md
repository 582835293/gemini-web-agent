# AgentLimb 极简备忘与高阶实战连招

- **本地安装路径**：`C:\tools\AgentLimb`（Windows 建议全英文路径）
- **Host 与数据目录**：`~/.agentlimb`（Windows 下为 `%USERPROFILE%\.agentlimb`）
- **MCP 配置文件**：`~/.gemini/config/mcp_config.json`（Windows 下为 `%USERPROFILE%\.gemini\config\mcp_config.json`，配置 `agentlimb`）

## 日常使用要点
1. **永久免弹窗与跨重启信任**：首次配对成功后信任状态持久化保存，后续启动 Antigravity 与 Chrome 自动连通，无需重配或点调试允许框。
2. **省 Token 调用原则（降轮次 + 砍无效回传 + 防 20s 超时）**：
   - 严禁截图与全页 `read_page`；将「调 `Extra High` + 拉满 `1048576` + 填 Prompt + 点 `Run`」合并在 **1 次 `javascript_eval`** 内并立即返回（注：`javascript_eval` 有 **20s CDP 执行上限**，勿在单次 JS 内死等长推理，发包后改用 `wait` 再另调一次 JS 提取）；
   - 提取 AI Studio 回答时**务必排除 `ms-thought-chunk, mat-expansion-panel` 思考块**，只返回最终正文。
3. **防后台冻结与防 Chrome 多文件下载拦截（通道 A 零上下文落盘关键）**：
   - **防后台冻结**：多标签页并行时，提取正文或点击导出前**先 `tab_activate(tabId)`** 唤醒渲染，并执行 `scrollIntoView()`，防止后台 Tab 暂停刷新；
   - **防连下拦截 + 不经 AI 上下文**：网页生成长源码（如 `index.html`、`story.json`）或批量音频/图片时，**严禁将几万字全文直接返回给本地 AI 重抄写入**，也不要在同一页连着触发多个 `<a download>`（Chrome 会拦截第 2 个之后的下载）；
   - **推荐做法**：在 JS 中把多个文本/JSON 产物打包成一个 `{ "index.html": "...", "story.json": "..." }` 对象用单个 `<a download="bundle.json">` 落入下载目录（或每个标签页只下 1 个二进制文件），随后本地一行命令直接归档解包：
     ```bash
     python scripts/gemini_web.py harvest --pattern "bundle*.json" --unpack-json --dest "./my-app"
     ```
4. **角色/画风一致性参考图改图闭环**：
   - 先在 `flow.google.com` 用 `Nano Banana 2.1`（`x1`，0 点数）生成角色基准立绘并下载 `1K/2K`；
   - 再用下方 `DataTransfer` 模板把基准图传进 AI Studio `gemini-nano-banana-2.1`，要求“保持原图角色五官、服饰与画风完全一致，仅调整表情为微笑/挥手”，可显著提升组图一致性。
5. **AI Studio Build 通道 A 导出流**：
   - 在 `aistudio.google.com/apps` 开启 `MAX` + `Gemini 4 Argon` 完成生成后，点击 `button[aria-label="Export options"]` 选择 `Download as .zip file`，再用 `gemini_web.py harvest --pattern "*.zip" --dest "./project"` 收割并解压，全程零代码回传到本地上下文。
6. **AI Studio 无弹窗传文件模板（实测可用）**：本地读出文件 Base64 后，在 AI Studio Tab 执行：
   ```js
   const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
   const inp = document.querySelector('ms-add-media-button input[type="file"], input.file-input');
   const dt = new DataTransfer();
   dt.items.add(new File([bytes], '设定.md', { type: 'text/markdown' }));
   inp.files = dt.files;
   inp.dispatchEvent(new Event('change', { bubbles: true }));
   ```
   待提示区显示文件名且无 `Loading...` 即可连同后续指令一起 `Run`（注意 `gemini.google.com` 拦截合成 `DataTransfer`，纯文本直接填输入框，大附件切 AI Studio 或用 `gemini_web.py --file`）。
7. **多账号并发与会话收尾**：Chrome 多 Profile 同时启用 AgentLimb 后，所有工具传 `browser: "<ProfileID或别名>"` 即可分担额度；任务结束调用 `agentlimb:say` 释放面板状态。

## 版本建议与已知兼容性排查（`>= v0.8.2`）
- **推荐版本**：请使用 **AgentLimb `v0.8.2` 及以上版本**（上游修复发布：https://github.com/hooosberg/AgentLimb/releases/tag/v0.8.2 ）。
- **已知问题（`v0.8.1` 及更早版本）**：当本地其他服务占用 `127.0.0.1:8765`~`8780` 端口并对 `/health` 返回非 2xx 响应（如 `404`）时，`v0.8.1` 扩展 Service Worker 的 `probe()` 未释放响应体，可能导致 Chrome 扩展渲染进程持续累积系统提交内存（感谢 [Issue #1](https://github.com/582835293/gemini-web-agent/issues/1) 与上游 [PR #3](https://github.com/hooosberg/AgentLimb/pull/3)）。
- **升级与临时规避**：
  1. 升级 AgentLimb 至 `v0.8.2+` 后，在 Chrome 打开 `chrome://extensions` 点击扩展的**重新加载**按钮。
  2. 若暂时无法升级且观察到内存异常增长：在 Chrome 中**暂时关闭 AgentLimb 扩展**（或释放占用 `127.0.0.1:8765` 的本地服务端口），并在 Chrome 地址栏打开 `chrome://inspect/#remote-debugging` 开启内置调试，改用本仓库内置的 **通道 B（`scripts/gemini_web.py` + `daemon`）**，切勿对默认 `User Data` 目录强杀重启 Chrome。
