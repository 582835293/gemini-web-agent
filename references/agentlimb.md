# AgentLimb 极简备忘

- **本地安装路径**：`C:\tools\AgentLimb`（Windows 建议全英文路径）
- **Host 与数据目录**：`~/.agentlimb`（Windows 下为 `%USERPROFILE%\.agentlimb`）
- **MCP 配置文件**：`~/.gemini/config/mcp_config.json`（Windows 下为 `%USERPROFILE%\.gemini\config\mcp_config.json`，配置 `agentlimb`）

## 日常使用要点
1. **永久免弹窗与跨重启信任**：首次配对成功后信任状态持久化保存，后续启动 Antigravity 与 Chrome 自动连通，无需重配或点调试允许框。
2. **省 Token 调用原则**：控制网页端 Gemini 时，优先使用 `javascript_eval` / `browser_batch` 直接定位实测锚点，避免反复截图与 `read_page` 消耗大量 Token。
3. **多账号并发**：Chrome 多 Profile 同时启用 AgentLimb 后，所有工具传 `browser: "<ProfileID或别名>"` 即可路由到不同账号分担额度。
4. **每次任务结束**：调用 `agentlimb:say` 释放面板状态。
