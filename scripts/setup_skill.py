#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gemini-web-agent 一键自动配置与环境自检脚本（Zero-Touch Setup for AI Agents）

用途：
  任何 AI Agent（Antigravity / Gemini CLI / Claude Code / Cursor / Codex）在拉取或克隆本仓库后，
  只需执行：python scripts/setup_skill.py --auto
  即可全自动完成：
    1. 自动识别并同步 Skill 到全局技能目录（默认优先 ~/.gemini/config/skills/gemini-web-agent）；
    2. 自动创建 .venv 并安装 requirements.txt（playwright, Pillow，无需下载 Chromium 浏览器内核）；
    3. 自动检测双通道状态（通道 A: AgentLimb MCP 配置；通道 B: 外部 Chrome CDP DevToolsActivePort）；
    4. 输出结构化 JSON 诊断报告，方便拉取者电脑上的 AI 直接接管并开始调度三端额度。
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

SKILL_NAME = "gemini-web-agent"
COPY_ITEMS = ("SKILL.md", "README.md", "requirements.txt", "references", "scripts")


def detect_target_skill_dir(source_root: Path, explicit_target: str = "") -> Path:
    """确定 Skill 最终安装目录；若当前已在某个已知 skills 目录中则原地初始化。"""
    if explicit_target:
        return Path(explicit_target).expanduser().resolve()

    home = Path.home()
    candidates = [
        home / ".gemini" / "config" / "skills",
        home / ".gemini" / "skills",
        home / ".agents" / "skills",
        home / ".claude" / "skills",
        home / ".cursor" / "skills",
    ]
    resolved_src = source_root.resolve()
    for parent in candidates:
        if resolved_src == (parent / SKILL_NAME).resolve():
            return resolved_src

    for parent in candidates:
        if parent.exists():
            return (parent / SKILL_NAME).resolve()

    return (candidates[0] / SKILL_NAME).resolve()


def sync_skill_files(source_root: Path, target_dir: Path) -> bool:
    """将仓库核心文件同步到全局 Skill 目录（跳过 .git / .venv / __pycache__）。"""
    if source_root.resolve() == target_dir.resolve():
        return False

    target_dir.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", "*.pyc", ".DS_Store")
    for item in COPY_ITEMS:
        src = source_root / item
        dst = target_dir / item
        if not src.exists():
            continue
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=ignore)
        else:
            shutil.copy2(src, dst)
    return True


def venv_python_path(skill_dir: Path) -> Path:
    if platform.system().lower().startswith("win"):
        return skill_dir / ".venv" / "Scripts" / "python.exe"
    return skill_dir / ".venv" / "bin" / "python"


def ensure_venv_and_deps(skill_dir: Path, skip_pip: bool = False) -> dict:
    """确保 .venv 存在并安装了 playwright 与 Pillow。"""
    py = venv_python_path(skill_dir)
    created_venv = False
    if not py.exists():
        venv_dir = skill_dir / ".venv"
        venv.EnvBuilder(with_pip=True).create(str(venv_dir))
        created_venv = True

    def check_imports() -> bool:
        proc = subprocess.run(
            [str(py), "-c", "import playwright, PIL; print('DEPS_OK')"],
            capture_output=True,
            text=True,
        )
        return proc.returncode == 0 and "DEPS_OK" in proc.stdout

    deps_ok = check_imports()
    installed_now = False
    pip_error = ""
    if not deps_ok and not skip_pip:
        req = skill_dir / "requirements.txt"
        cmd = [str(py), "-m", "pip", "install", "-q", "-r", str(req)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            # 若默认源较慢或失败，自动尝试清华镜像兜底
            mirror_cmd = [
                str(py),
                "-m",
                "pip",
                "install",
                "-q",
                "-i",
                "https://pypi.tuna.tsinghua.edu.cn/simple",
                "-r",
                str(req),
            ]
            proc2 = subprocess.run(mirror_cmd, capture_output=True, text=True)
            if proc2.returncode != 0:
                pip_error = (proc2.stderr or proc.stderr or "").strip()
        deps_ok = check_imports()
        installed_now = deps_ok

    return {
        "venv_python": str(py),
        "venv_created": created_venv,
        "dependencies_ready": deps_ok,
        "installed_now": installed_now,
        "pip_error": pip_error or None,
    }


def detect_agentlimb_mcp() -> dict:
    """扫描本机常见 AI 客户端 MCP 配置，检查是否已配置 agentlimb。"""
    home = Path.home()
    mcp_files = [
        home / ".gemini" / "config" / "mcp_config.json",
        home / ".gemini" / "antigravity" / "mcp_config.json",
        home / ".claude" / "claude_desktop_config.json",
        home / ".cursor" / "mcp.json",
    ]
    if platform.system().lower().startswith("win"):
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        mcp_files.append(appdata / "Claude" / "claude_desktop_config.json")

    found_configs = []
    agentlimb_configured_in = []
    for path in mcp_files:
        if not path.exists():
            continue
        found_configs.append(str(path))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            servers = data.get("mcpServers", {})
            if "agentlimb" in servers and not servers["agentlimb"].get("disabled", False):
                agentlimb_configured_in.append(str(path))
        except Exception:
            pass

    return {
        "configured": len(agentlimb_configured_in) > 0,
        "configured_files": agentlimb_configured_in,
        "scanned_mcp_configs": found_configs,
    }


def detect_chrome_cdp() -> dict:
    """检测本机 Chrome 可执行路径与 DevToolsActivePort 状态。"""
    sys_name = platform.system().lower()
    active_ports = []
    chrome_bins = []

    if sys_name.startswith("win"):
        local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        active_ports.append(local_app / "Google" / "Chrome" / "User Data" / "DevToolsActivePort")
        chrome_bins.extend([
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            local_app / "Google" / "Chrome" / "Application" / "chrome.exe",
        ])
    elif sys_name == "darwin":
        active_ports.append(Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "DevToolsActivePort")
        chrome_bins.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))
    else:
        active_ports.append(Path.home() / ".config" / "google-chrome" / "DevToolsActivePort")
        for cmd in ("google-chrome", "chromium", "chromium-browser"):
            which = shutil.which(cmd)
            if which:
                chrome_bins.append(Path(which))

    cdp_ws_url = None
    active_port_file = None
    for port_file in active_ports:
        if port_file.exists():
            lines = [l.strip() for l in port_file.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
            if len(lines) >= 2:
                active_port_file = str(port_file)
                cdp_ws_url = f"ws://127.0.0.1:{lines[0]}{lines[1]}"
                break

    found_chrome = next((str(p) for p in chrome_bins if p.exists()), None)
    return {
        "cdp_active": cdp_ws_url is not None,
        "active_port_file": active_port_file,
        "cdp_ws_url": cdp_ws_url,
        "chrome_executable": found_chrome,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="gemini-web-agent 自动安装与环境诊断工具")
    parser.add_argument("--auto", action="store_true", help="自动同步到全局 Skills 目录并初始化 .venv 依赖")
    parser.add_argument("--target", default="", help="手动指定 Skill 安装目标路径")
    parser.add_argument("--skip-pip", action="store_true", help="仅检查不自动执行 pip 安装")
    args = parser.parse_args()

    source_root = Path(__file__).resolve().parent.parent
    target_dir = detect_target_skill_dir(source_root, args.target)

    synced = False
    if args.auto or args.target:
        synced = sync_skill_files(source_root, target_dir)
    else:
        target_dir = source_root.resolve()

    venv_info = ensure_venv_and_deps(target_dir, skip_pip=args.skip_pip)
    agentlimb_info = detect_agentlimb_mcp()
    cdp_info = detect_chrome_cdp()

    next_actions = []
    if not venv_info["dependencies_ready"]:
        next_actions.append(
            f"请检查网络并手动执行: \"{venv_info['venv_python']}\" -m pip install -r \"{target_dir / 'requirements.txt'}\""
        )
    if not agentlimb_info["configured"] and not cdp_info["cdp_active"]:
        chrome_cmd = (
            f'"{cdp_info["chrome_executable"]}" --remote-debugging-port=9222'
            if cdp_info["chrome_executable"]
            else "chrome --remote-debugging-port=9222"
        )
        next_actions.append(
            "未检测到 AgentLimb MCP 与已开启的 Chrome 远程调试端口。推荐二选一："
            " (1) 安装并启用 AgentLimb MCP（永久免弹窗，参见 references/agentlimb.md）；"
            f" 或 (2) 关闭现有 Chrome 后用 `{chrome_cmd}` 重启 Chrome 启用通道 B CDP 脚本。"
        )
    elif agentlimb_info["configured"]:
        next_actions.append("通道 A (AgentLimb MCP) 已就绪，可直接操控已登录外部 Chrome；通道 B (gemini_web.py) 已配齐备用。")
    else:
        next_actions.append(
            f"通道 B (Chrome CDP) 已就绪，可运行测试命令: \"{venv_info['venv_python']}\" \"{target_dir / 'scripts' / 'gemini_web.py'}\" usage --include-flow"
        )

    report = {
        "ok": venv_info["dependencies_ready"],
        "skill_name": SKILL_NAME,
        "source_dir": str(source_root.resolve()),
        "installed_skill_dir": str(target_dir),
        "files_synced_to_global": synced,
        "cli_script": str(target_dir / "scripts" / "gemini_web.py"),
        "venv": venv_info,
        "channel_a_agentlimb": agentlimb_info,
        "channel_b_cdp": cdp_info,
        "next_actions": next_actions,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not venv_info["dependencies_ready"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
