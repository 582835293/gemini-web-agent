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
import tempfile
import time
import urllib.error
import urllib.request
import venv
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SKILL_NAME = "gemini-web-agent"
REPO_SLUG = "582835293/gemini-web-agent"
REPO_URL = f"https://github.com/{REPO_SLUG}.git"
DEFAULT_BRANCH = "main"
VERSION_FILE_NAME = ".skill_version.json"
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
        home / ".codex" / "skills",
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


def _has_enabled_agentlimb_json(data: dict) -> bool:
    servers = data.get("mcpServers", {})
    if isinstance(servers, dict) and "agentlimb" in servers:
        if not servers["agentlimb"].get("disabled", False):
            return True
    projects = data.get("projects", {})
    if isinstance(projects, dict):
        for proj_cfg in projects.values():
            if not isinstance(proj_cfg, dict):
                continue
            p_servers = proj_cfg.get("mcpServers", {})
            if isinstance(p_servers, dict) and "agentlimb" in p_servers:
                if not p_servers["agentlimb"].get("disabled", False):
                    return True
    return False


def _has_enabled_agentlimb_toml(raw_text: str) -> bool:
    try:
        import tomllib
        data = tomllib.loads(raw_text)
        mcp_servers = data.get("mcp_servers", {})
        if isinstance(mcp_servers, dict) and "agentlimb" in mcp_servers:
            entry = mcp_servers["agentlimb"]
            if isinstance(entry, dict):
                return entry.get("enabled", True) is not False
            return True
    except Exception:
        pass
    return "[mcp_servers.agentlimb]" in raw_text


def detect_agentlimb_mcp() -> dict:
    """扫描本机常见 AI 客户端 MCP 配置，检查是否已配置 agentlimb。"""
    home = Path.home()
    mcp_files = [
        home / ".gemini" / "config" / "mcp_config.json",
        home / ".gemini" / "antigravity" / "mcp_config.json",
        home / ".claude.json",
        home / ".claude" / "claude_desktop_config.json",
        home / ".codex" / "config.toml",
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
            raw = path.read_text(encoding="utf-8")
            if path.suffix == ".toml":
                if _has_enabled_agentlimb_toml(raw):
                    agentlimb_configured_in.append(str(path))
            else:
                data = json.loads(raw)
                if isinstance(data, dict) and _has_enabled_agentlimb_json(data):
                    agentlimb_configured_in.append(str(path))
        except Exception:
            pass

    return {
        "configured": len(agentlimb_configured_in) > 0,
        "configured_files": agentlimb_configured_in,
        "scanned_mcp_configs": found_configs,
    }


def _probe_cdp_http(port: str, timeout_sec: float = 1.5) -> dict | None:
    """探测 Chrome CDP HTTP 端口 /json/version（绕过系统代理）。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(f"http://127.0.0.1:{port}/json/version", method="GET")
    try:
        with opener.open(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None
    return None


def detect_chrome_cdp() -> dict:
    """检测本机 Chrome 可执行路径、DevToolsActivePort 状态与实际 HTTP/WS 就绪模式。"""
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
    cdp_mode = "inactive"
    cdp_http_ready = False
    for port_file in active_ports:
        if port_file.exists():
            lines = [l.strip() for l in port_file.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
            if len(lines) >= 2:
                active_port_file = str(port_file)
                port = lines[0]
                cdp_ws_url = f"ws://127.0.0.1:{port}{lines[1]}"
                ver = _probe_cdp_http(port)
                if ver:
                    cdp_http_ready = True
                    cdp_mode = "http_ready"
                else:
                    cdp_mode = "chrome_ui_approval_required"
                break

    found_chrome = next((str(p) for p in chrome_bins if p.exists()), None)
    return {
        "cdp_active": cdp_ws_url is not None,
        "cdp_http_ready": cdp_http_ready,
        "cdp_mode": cdp_mode,
        "active_port_file": active_port_file,
        "cdp_ws_url": cdp_ws_url,
        "chrome_executable": found_chrome,
    }


def _get_git_commit(repo_dir: Path) -> str:
    if not (repo_dir / ".git").exists():
        return ""
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _read_version_meta(skill_dir: Path) -> dict:
    meta_file = skill_dir / VERSION_FILE_NAME
    if not meta_file.exists():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_version_meta(skill_dir: Path, source_root: Path, commit: str = "", last_checked_at: str = "") -> dict:
    meta = _read_version_meta(skill_dir)
    now_iso = datetime.now(timezone.utc).isoformat()
    resolved_commit = commit or _get_git_commit(source_root) or meta.get("installed_commit", "")
    meta.update({
        "repo": REPO_URL,
        "branch": DEFAULT_BRANCH,
        "source_dir": str(source_root.resolve()),
        "installed_commit": resolved_commit,
        "installed_at": now_iso,
    })
    if last_checked_at:
        meta["last_checked_at"] = last_checked_at
    (skill_dir / VERSION_FILE_NAME).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def _fetch_remote_head(timeout_sec: float = 4.0) -> tuple[str, str, str]:
    """返回 (remote_commit_short, commit_message, error_msg)。优先 GitHub API，兜底 git ls-remote。"""
    api_url = f"https://api.github.com/repos/{REPO_SLUG}/commits/{DEFAULT_BRANCH}"
    req = urllib.request.Request(
        api_url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "gemini-web-agent-updater"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            sha = str(data.get("sha", ""))[:7]
            msg = str(data.get("commit", {}).get("message", "")).splitlines()[0]
            if sha:
                return sha, msg, ""
    except Exception as api_err:
        err_msg = str(api_err)
    else:
        err_msg = "GitHub API 未返回 sha"

    try:
        proc = subprocess.run(
            ["git", "ls-remote", REPO_URL, f"refs/heads/{DEFAULT_BRANCH}"],
            capture_output=True,
            text=True,
            timeout=int(max(timeout_sec, 5)),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            sha = proc.stdout.strip().split()[0][:7]
            return sha, "", ""
        if proc.stderr.strip():
            err_msg = proc.stderr.strip()
    except Exception as git_err:
        err_msg = f"{err_msg}; {git_err}"
    return "", "", err_msg


def check_for_updates(skill_dir: Path, source_root: Path, cache_hours: float = 0.0) -> dict:
    """检测 GitHub 远端 main 分支是否有更新。cache_hours>0 时命中缓存则跳过联网。"""
    meta = _read_version_meta(skill_dir)
    if not meta:
        meta = _read_version_meta(source_root)
    local_commit = _get_git_commit(source_root) or meta.get("installed_commit", "")
    last_checked = meta.get("last_checked_at", "")

    if cache_hours > 0 and last_checked:
        try:
            last_dt = datetime.fromisoformat(last_checked.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600.0
            if age_hours < cache_hours:
                return {
                    "checked_network": False,
                    "cache_hit": True,
                    "cache_age_hours": round(age_hours, 2),
                    "local_commit": local_commit or None,
                    "remote_commit": meta.get("remote_commit") or None,
                    "has_update": bool(
                        local_commit and meta.get("remote_commit") and not local_commit.startswith(meta["remote_commit"][:7])
                    ),
                    "update_command": f'python "{Path(__file__).resolve()}" --update',
                }
        except Exception:
            pass

    remote_sha, remote_msg, err = _fetch_remote_head()
    now_iso = datetime.now(timezone.utc).isoformat()
    if remote_sha:
        meta["remote_commit"] = remote_sha
        meta["last_checked_at"] = now_iso
        target_meta_dir = skill_dir if skill_dir.exists() else source_root
        try:
            (target_meta_dir / VERSION_FILE_NAME).write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    has_update = bool(remote_sha and (not local_commit or not local_commit.startswith(remote_sha[:7])))
    return {
        "checked_network": True,
        "cache_hit": False,
        "local_commit": local_commit or None,
        "remote_commit": remote_sha or None,
        "remote_message": remote_msg or None,
        "has_update": has_update,
        "error": err or None,
        "update_command": f'python "{Path(__file__).resolve()}" --update',
    }


def apply_update(source_root: Path, target_dir: Path, skip_pip: bool = False) -> dict:
    """自动更新 Skill：优先 git pull，无 .git 时从 GitHub archive zip 拉取，并重同步至全局目录。"""
    meta = _read_version_meta(target_dir) or _read_version_meta(source_root)
    candidate_src = Path(meta["source_dir"]) if meta.get("source_dir") else source_root
    if not candidate_src.exists():
        candidate_src = source_root

    old_commit = _get_git_commit(candidate_src) or meta.get("installed_commit", "")
    method = ""
    if (candidate_src / ".git").exists():
        method = "git_pull"
        proc = subprocess.run(
            ["git", "-C", str(candidate_src), "pull", "--ff-only", "origin", DEFAULT_BRANCH],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git pull 失败（可能存在未提交本地修改）: {proc.stderr.strip() or proc.stdout.strip()}")
        new_commit = _get_git_commit(candidate_src)
        synced = sync_skill_files(candidate_src, target_dir)
    else:
        method = "github_zip"
        zip_url = f"https://github.com/{REPO_SLUG}/archive/refs/heads/{DEFAULT_BRANCH}.zip"
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "repo.zip"
            req = urllib.request.Request(zip_url, headers={"User-Agent": "gemini-web-agent-updater"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                zip_path.write_bytes(resp.read())
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp)
            extracted_root = next(Path(tmp).glob(f"{SKILL_NAME}-*"))
            synced = sync_skill_files(extracted_root, target_dir)
            candidate_src = target_dir
        remote_sha, _, _ = _fetch_remote_head()
        new_commit = remote_sha

    venv_info = ensure_venv_and_deps(target_dir, skip_pip=skip_pip)
    now_iso = datetime.now(timezone.utc).isoformat()
    _write_version_meta(target_dir, candidate_src, commit=new_commit, last_checked_at=now_iso)
    return {
        "updated": True,
        "method": method,
        "previous_commit": old_commit or None,
        "current_commit": new_commit or None,
        "files_synced_to_global": synced,
        "installed_skill_dir": str(target_dir),
        "venv": venv_info,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="gemini-web-agent 自动安装、版本检测与更新工具")
    parser.add_argument("--auto", action="store_true", help="自动同步到全局 Skills 目录并初始化 .venv 依赖")
    parser.add_argument("--target", default="", help="手动指定 Skill 安装目标路径")
    parser.add_argument("--skip-pip", action="store_true", help="仅检查不自动执行 pip 安装")
    parser.add_argument("--check-update", action="store_true", help="立即联网检查 GitHub 是否有新版本")
    parser.add_argument("--check-if-stale", action="store_true", help="仅当距离上次检查超过 --cache-hours 小时才联网查更新")
    parser.add_argument("--cache-hours", type=float, default=24.0, help="自动更新检查缓存小时数（默认 24 小时）")
    parser.add_argument("--update", action="store_true", help="自动从 GitHub 拉取最新版并重新同步全局 Skill 目录")
    args = parser.parse_args()

    source_root = Path(__file__).resolve().parent.parent
    target_dir = detect_target_skill_dir(source_root, args.target)

    if args.update:
        try:
            res = apply_update(source_root, target_dir, skip_pip=args.skip_pip)
            print(json.dumps({"ok": True, **res}, ensure_ascii=False, indent=2))
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2))
            sys.exit(1)
        return

    if args.check_update or args.check_if_stale:
        cache_h = args.cache_hours if args.check_if_stale and not args.check_update else 0.0
        res = check_for_updates(target_dir if target_dir.exists() else source_root, source_root, cache_hours=cache_h)
        print(json.dumps({"ok": True, "skill_name": SKILL_NAME, **res}, ensure_ascii=False, indent=2))
        return

    synced = False
    if args.auto or args.target:
        synced = sync_skill_files(source_root, target_dir)
    else:
        target_dir = source_root.resolve()

    if synced or not (target_dir / VERSION_FILE_NAME).exists():
        _write_version_meta(target_dir, source_root)

    venv_info = ensure_venv_and_deps(target_dir, skip_pip=args.skip_pip)
    agentlimb_info = detect_agentlimb_mcp()
    cdp_info = detect_chrome_cdp()
    version_meta = _read_version_meta(target_dir)

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
    elif agentlimb_info["configured"] and cdp_info["cdp_mode"] == "chrome_ui_approval_required":
        next_actions.append(
            "通道 A (AgentLimb MCP) 已就绪。检测到 Chrome 当前通过浏览器内开关监听调试端口（/json/version 未暴露），"
            "通道 B 若出现连接超时：请在 Chrome 弹出的「允许远程调试」框点击允许，或改用 --remote-debugging-port=9222 启动 Chrome。"
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
        "installed_commit": version_meta.get("installed_commit") or None,
        "source_dir": str(source_root.resolve()),
        "installed_skill_dir": str(target_dir),
        "files_synced_to_global": synced,
        "cli_script": str(target_dir / "scripts" / "gemini_web.py"),
        "quota_monitor_script": str(target_dir / "scripts" / "inspect_antigravity.py"),
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
