# AgentLimb 极简备忘

- **本地安装路径**：`C:\tools\AgentLimb`（Windows 建议全英文路径）
- **Host 与数据目录**：`~/.agentlimb`（Windows 下为 `%USERPROFILE%\.agentlimb`）
- **MCP 配置文件**：`~/.gemini/config/mcp_config.json`（Windows 下为 `%USERPROFILE%\.gemini\config\mcp_config.json`，配置 `agentlimb`）

## 日常使用要点
1. **永久免弹窗与跨重启信任**：首次配对成功后信任状态持久化保存，后续启动 Antigravity 与 Chrome 自动连通，无需重配或点调试允许框。
2. **省 Token 调用原则**：控制网页端 Gemini 时，优先使用 `javascript_eval` / `browser_batch` 直接定位实测锚点，避免反复截图与 `read_page` 消耗大量 Token。
3. **多账号并发**：Chrome 多 Profile 同时启用 AgentLimb 后，所有工具传 `browser: "<ProfileID或别名>"` 即可路由到不同账号分担额度。
4. **每次任务结束**：调用 `agentlimb:say` 释放面板状态。

## 版本建议与已知兼容性排查（`>= v0.8.2`）
- **推荐版本**：请使用 **AgentLimb `v0.8.2` 及以上版本**（上游修复发布：https://github.com/hooosberg/AgentLimb/releases/tag/v0.8.2 ）。
- **已知问题（`v0.8.1` 及更早版本）**：当本地其他服务占用 `127.0.0.1:8765`~`8780` 端口并对 `/health` 返回非 2xx 响应（如 `404`）时，`v0.8.1` 扩展 Service Worker 的 `probe()` 未释放响应体，可能导致 Chrome 扩展渲染进程持续累积系统提交内存（感谢 [Issue #1](https://github.com/582835293/gemini-web-agent/issues/1) 与上游 [PR #3](https://github.com/hooosberg/AgentLimb/pull/3)）。
- **升级与临时规避**：
  1. 升级 AgentLimb 至 `v0.8.2+` 后，在 Chrome 打开 `chrome://extensions` 点击扩展的**重新加载**按钮。
  2. 若暂时无法升级且观察到内存异常增长：在 Chrome 中**暂时关闭 AgentLimb 扩展**（或释放占用 `127.0.0.1:8765` 的本地服务端口），改用本仓库内置的 **通道 B（`scripts/gemini_web.py` + Chrome CDP `--remote-debugging-port=9222`）**。
