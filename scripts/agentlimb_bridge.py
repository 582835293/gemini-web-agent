#!/usr/bin/env python3
"""
AgentLimb 本地 HTTP Bridge 直连适配层（纯标准库实现，零第三方依赖）。

功能定位：
1. 自动探测本机运行中的 AgentLimb Bridge（默认扫描 127.0.0.1:8765..8780 `/health`）。
2. 探测 Bridge 是否支持高速 HTTP RPC (`POST /api/tool`)；若遇到未开启 `/api/tool` 的旧版/原版
   AgentLimb，精确标记 `api_tool_supported=False` 以便上层优雅回退到 MCP `browser_batch`。
3. 暴露与 Playwright 高度兼容的 `AgentLimbBrowser` / `AgentLimbContext` / `AgentLimbPage` /
   `AgentLimbLocator` 接口，让 `gemini_web.py` 的 `ask` / `playground` / `flow` / `usage` /
   `task-net` / `doctor` / `wave` 无需重构业务逻辑即可通过单条 CLI 命令高速驱动日常 Chrome。
"""

from __future__ import annotations

import base64
import contextlib
import json
import mimetypes
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_AGENTLIMB_PORTS: list[int] = list(range(8765, 8781))
DEFAULT_HOST = "127.0.0.1"


def _build_direct_opener():
    """构建绕过系统代理的本地 HTTP opener，避免 127.0.0.1 误走 HTTP_PROXY。"""
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _http_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    timeout_sec: float = 1.0,
) -> tuple[int, dict | None, str]:
    """发起本地 HTTP JSON 请求，返回 `(status_code, json_body_or_none, raw_text)`。"""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = _build_direct_opener()
    try:
        with opener.open(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw.strip() else None
            except json.JSONDecodeError:
                parsed = None
            return int(resp.status), parsed, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw.strip() else None
        except json.JSONDecodeError:
            parsed = None
        return int(exc.code), parsed, raw


def _translate_bridge_error(message: str) -> str:
    """将 AgentLimb 常见英文底层报错转化为可直接执行的中文排查提示。"""
    low = (message or "").lower()
    if "no current window" in low:
        return "AgentLimb 桥接已连接，但当前日常 Chrome 没有打开的浏览器窗口（No current window），请先打开一个 Chrome 窗口后重试。"
    if "not authorized" in low:
        return "AgentLimb 扩展尚未授权当前本地会话，请在 Chrome 打开 AgentLimb 侧栏点击「复制连接提示词」授权后重试。"
    if "no browser extension connected" in low or "awaiting_extension" in low:
        return "未检测到 AgentLimb Chrome 扩展连接，请确认日常 Chrome 已启动且开启 AgentLimb 扩展。"
    return message


def probe_agentlimb_port(
    port: int,
    timeout_sec: float = 0.45,
    check_api_tool: bool = False,
) -> dict | None:
    """探测单个本地 AgentLimb Bridge 端口 `/health` 与可选 `/api/tool` 支持情况。"""
    base_url = f"http://{DEFAULT_HOST}:{int(port)}"
    try:
        status, data, _ = _http_json(f"{base_url}/health", method="GET", timeout_sec=timeout_sec)
    except Exception:
        return None
    if status != 200 or not isinstance(data, dict):
        return None
    if not data.get("ok") or data.get("service") != "agentlimb-bridge":
        return None

    info = {
        "running": True,
        "port": int(data.get("port") or port),
        "base_url": base_url,
        "version": str(data.get("version") or ""),
        "stage": str(data.get("stage") or ""),
        "authorized": bool(data.get("authorized")),
        "paired": bool(data.get("paired")),
        "browsers": int(data.get("browsers") or 0),
        "browser_list": data.get("browserList") if isinstance(data.get("browserList"), list) else [],
        "denied": data.get("denied"),
        "api_tool_supported": None,
        "api_tool_ping_ok": None,
        "api_tool_error": None,
    }
    if check_api_tool:
        try:
            t_status, t_data, t_raw = _http_json(
                f"{base_url}/api/tool",
                method="POST",
                payload={"tool": "ping", "arguments": {}, "timeoutMs": 4000},
                timeout_sec=max(1.5, timeout_sec * 4),
            )
            if t_status == 200 and isinstance(t_data, dict) and "ok" in t_data:
                info["api_tool_supported"] = True
                info["api_tool_ping_ok"] = bool(t_data.get("ok"))
                if not t_data.get("ok"):
                    info["api_tool_error"] = str(t_data.get("error") or "")
            else:
                info["api_tool_supported"] = False
                if t_status != 404:
                    info["api_tool_error"] = t_raw[:160]
        except Exception as exc:
            info["api_tool_supported"] = False
            info["api_tool_error"] = str(exc)
    return info


def discover_agentlimb_bridge(
    port_override: int | None = None,
    check_api_tool: bool = True,
    ports: list[int] | None = None,
) -> dict:
    """扫描本地 AgentLimb Bridge 候选端口，优先返回已授权且支持 `/api/tool` 的实例。"""
    if port_override is not None:
        candidate_ports = [int(port_override)]
    else:
        env_ports = (os.environ.get("AGENTLIMB_BRIDGE_PORTS") or "").strip()
        if env_ports:
            parsed = [int(p.strip()) for p in env_ports.split(",") if p.strip().isdigit()]
            candidate_ports = parsed or DEFAULT_AGENTLIMB_PORTS
        else:
            candidate_ports = list(ports or DEFAULT_AGENTLIMB_PORTS)

    found: list[dict] = []
    for p in candidate_ports:
        res = probe_agentlimb_port(p, timeout_sec=0.35, check_api_tool=check_api_tool)
        if res is not None:
            found.append(res)

    if not found:
        return {
            "running": False,
            "port": None,
            "base_url": None,
            "authorized": False,
            "api_tool_supported": False,
            "browsers": 0,
            "browser_list": [],
            "candidates_found": 0,
        }

    found.sort(
        key=lambda item: (
            0 if item.get("api_tool_supported") else 1,
            0 if item.get("authorized") else 1,
            0 if int(item.get("browsers") or 0) > 0 else 1,
            int(item.get("port") or 99999),
        )
    )
    best = dict(found[0])
    best["candidates_found"] = len(found)
    return best


def _unwrap_tool_result(resp: dict) -> object:
    """解包 AgentLimb `/api/tool` 的外层/内层嵌套结构。"""
    if not isinstance(resp, dict):
        return resp
    if not resp.get("ok"):
        raise RuntimeError(_translate_bridge_error(str(resp.get("error") or "AgentLimb tool 调用失败")))
    outer = resp.get("result")
    if isinstance(outer, dict) and "result" in outer:
        return outer.get("result")
    return outer


def _unwrap_eval_payload(raw_res: object) -> tuple[object, str]:
    """从 `javascript_eval` 返回值中提取 `__gwa` 包装后的值与最新页面 URL。"""
    cur = raw_res
    for _ in range(3):
        if isinstance(cur, dict) and cur.get("__gwa") == 1:
            if not cur.get("ok", True):
                raise RuntimeError(str(cur.get("error") or "页面 JS 执行失败"))
            return cur.get("val"), str(cur.get("href") or "")
        if isinstance(cur, dict):
            if "value" in cur and len(cur) <= 3:
                cur = cur.get("value")
                continue
            if "result" in cur and len(cur) <= 3:
                cur = cur.get("result")
                continue
        break
    return cur, ""


# 注入每次查询表达式的轻量 Playwright 选择器引擎（自包含，页面跳转后不依赖残留状态）。
# 支持标准 CSS、逗号分组、组合器（空格 / > / + / ~）、:visible、:has-text("...")、:text-is("...") 以及链式 filter/nth。
_GWA_DOM_HELPER_JS = r"""
const __gwaIsVisible = (el) => {
  if (!el || el.nodeType !== 1) return false;
  const style = window.getComputedStyle(el);
  if (!style || style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
  const r = el.getBoundingClientRect();
  return (r.width > 0 && r.height > 0) || el.getClientRects().length > 0;
};
const __gwaNormText = (el) => String((el && (el.innerText !== undefined ? el.innerText : el.textContent)) || '');
const __gwaSplitTop = (str, sepRe) => {
  const out = [];
  let buf = '';
  let quote = '';
  let depth = 0;
  for (let i = 0; i < str.length; i++) {
    const ch = str[i];
    if (quote) {
      buf += ch;
      if (ch === quote && str[i - 1] !== '\\') quote = '';
      continue;
    }
    if (ch === '"' || ch === "'") {
      quote = ch;
      buf += ch;
      continue;
    }
    if (ch === '(' || ch === '[') { depth++; buf += ch; continue; }
    if (ch === ')' || ch === ']') { if (depth > 0) depth--; buf += ch; continue; }
    if (depth === 0 && sepRe.test(ch)) {
      if (buf.trim()) out.push(buf.trim());
      buf = '';
      continue;
    }
    buf += ch;
  }
  if (buf.trim()) out.push(buf.trim());
  return out;
};
const __gwaTokenizeBranch = (branch) => {
  const tokens = [];
  let cur = '';
  let comb = ' ';
  let quote = '';
  let depth = 0;
  for (let i = 0; i < branch.length; i++) {
    const ch = branch[i];
    if (quote) {
      cur += ch;
      if (ch === quote && branch[i - 1] !== '\\') quote = '';
      continue;
    }
    if (ch === '"' || ch === "'") { quote = ch; cur += ch; continue; }
    if (ch === '(' || ch === '[') { depth++; cur += ch; continue; }
    if (ch === ')' || ch === ']') { if (depth > 0) depth--; cur += ch; continue; }
    if (depth === 0 && (ch === ' ' || ch === '\t' || ch === '\n' || ch === '>' || ch === '+' || ch === '~')) {
      if (cur.trim()) {
        tokens.push({ comb, raw: cur.trim() });
        cur = '';
        comb = (ch === '>' || ch === '+' || ch === '~') ? ch : ' ';
      } else if (ch === '>' || ch === '+' || ch === '~') {
        comb = ch;
      }
      continue;
    }
    cur += ch;
  }
  if (cur.trim()) tokens.push({ comb, raw: cur.trim() });
  return tokens;
};
const __gwaCompileStep = (raw) => {
  let css = raw;
  let needVisible = false;
  const hasTexts = [];
  const exactTexts = [];
  let changed = true;
  while (changed) {
    changed = false;
    const visIdx = css.search(/:visible(?![a-zA-Z0-9_-])/);
    if (visIdx >= 0) {
      needVisible = true;
      css = css.slice(0, visIdx) + css.slice(visIdx + 8);
      changed = true;
      continue;
    }
    const m = css.match(/:(has-text|text-is)\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|([^)]+))\s*\)/);
    if (m) {
      const val = (m[2] ?? m[3] ?? m[4] ?? '').replace(/\\(["'])/g, '$1');
      if (m[1] === 'has-text') hasTexts.push(val.toLowerCase());
      else exactTexts.push(val.trim());
      css = css.slice(0, m.index) + css.slice(m.index + m[0].length);
      changed = true;
    }
  }
  css = css.trim() || '*';
  return { css, needVisible, hasTexts, exactTexts };
};
const __gwaMatchFilters = (el, spec) => {
  if (!el || el.nodeType !== 1) return false;
  if (spec.needVisible && !__gwaIsVisible(el)) return false;
  if (spec.hasTexts.length || spec.exactTexts.length) {
    const rawTxt = __gwaNormText(el);
    const lowTxt = rawTxt.toLowerCase();
    for (const needle of spec.hasTexts) {
      if (!lowTxt.includes(needle)) return false;
    }
    const trimTxt = rawTxt.trim();
    for (const exact of spec.exactTexts) {
      if (trimTxt !== exact) return false;
    }
  }
  return true;
};
const __gwaQueryBranch = (roots, branch) => {
  const tokens = __gwaTokenizeBranch(branch);
  if (!tokens.length) return [];
  let current = roots;
  for (let idx = 0; idx < tokens.length; idx++) {
    const { comb, raw } = tokens[idx];
    const spec = __gwaCompileStep(raw);
    const next = [];
    const seen = new Set();
    for (const r of current) {
      if (!r || !r.querySelectorAll) continue;
      let cands = [];
      if (comb === '>') {
        for (const ch of (r.children || [])) {
          try { if (ch.matches(spec.css)) cands.push(ch); } catch (_) {}
        }
      } else if (comb === '+') {
        const sib = r.nextElementSibling;
        try { if (sib && sib.matches(spec.css)) cands.push(sib); } catch (_) {}
      } else if (comb === '~') {
        let sib = r.nextElementSibling;
        while (sib) {
          try { if (sib.matches(spec.css)) cands.push(sib); } catch (_) {}
          sib = sib.nextElementSibling;
        }
      } else {
        try { cands = Array.from(r.querySelectorAll(spec.css)); } catch (_) { cands = []; }
      }
      for (const el of cands) {
        if (!seen.has(el) && __gwaMatchFilters(el, spec)) {
          seen.add(el);
          next.push(el);
        }
      }
    }
    current = next;
    if (!current.length) break;
  }
  return current;
};
const __gwaResolveChain = (chain) => {
  let current = [document];
  for (const step of chain) {
    if (step.selector) {
      const branches = __gwaSplitTop(step.selector, /^,$/);
      const matched = [];
      const seen = new Set();
      for (const br of branches) {
        for (const el of __gwaQueryBranch(current, br)) {
          if (!seen.has(el)) { seen.add(el); matched.push(el); }
        }
      }
      current = matched;
    }
    if (step.hasTextRegex) {
      const re = new RegExp(step.hasTextRegex, step.hasTextFlags || '');
      current = current.filter(el => re.test(__gwaNormText(el)));
    }
    if (step.nth !== undefined && step.nth !== null) {
      if (step.nth === -1) current = current.length ? [current[current.length - 1]] : [];
      else if (step.nth >= 0 && step.nth < current.length) current = [current[step.nth]];
      else current = [];
    }
    if (!current.length) break;
  }
  return current;
};
"""


class AgentLimbBridgeClient:
    """AgentLimb 本地 HTTP Bridge `/api/tool` 轻量客户端。"""

    def __init__(
        self,
        base_url: str,
        browser_profile: str = "",
        port: int | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.browser_profile = (browser_profile or "").strip()
        self.port = port

    def call_tool(self, tool: str, arguments: dict | None = None, timeout_ms: int = 65000) -> object:
        args = dict(arguments or {})
        if self.browser_profile and "browser" not in args:
            args["browser"] = self.browser_profile
        payload = {"tool": tool, "arguments": args, "timeoutMs": int(timeout_ms)}
        http_timeout = max(5.0, (int(timeout_ms) / 1000.0) + 10.0)
        status, data, raw = _http_json(
            f"{self.base_url}/api/tool",
            method="POST",
            payload=payload,
            timeout_sec=http_timeout,
        )
        if status != 200 or not isinstance(data, dict):
            raise RuntimeError(f"AgentLimb /api/tool 返回异常 (HTTP {status}): {raw[:200]}")
        return _unwrap_tool_result(data)

    def batch(self, actions: list[dict], timeout_ms: int = 65000) -> object:
        """打包执行多步浏览器动作（每批最多 20 步，自动分片）。"""
        last_res = None
        for idx in range(0, len(actions), 20):
            chunk = actions[idx : idx + 20]
            args: dict = {"actions": chunk}
            if self.browser_profile:
                args["browser"] = self.browser_profile
            last_res = self.call_tool("browser_batch", args, timeout_ms=timeout_ms)
        return last_res

    def say(self, text: str) -> object:
        clean = (text or "").strip()
        if not clean:
            return None
        return self.call_tool("say", {"text": clean}, timeout_ms=10000)


class AgentLimbKeyboard:
    """兼容 `page.keyboard.press(...)`。"""

    def __init__(self, page: AgentLimbPage):
        self._page = page

    def press(self, key: str) -> None:
        key_name, modifiers = _split_key_and_modifiers(key)
        args: dict = {"action": "key", "tabId": self._page.tab_id, "key": key_name}
        if modifiers:
            args["modifiers"] = modifiers
        self._page.bridge.call_tool("computer", args, timeout_ms=15000)


def _split_key_and_modifiers(key_combo: str) -> tuple[str, str]:
    parts = [p.strip() for p in (key_combo or "").split("+") if p.strip()]
    if not parts:
        return "Enter", ""
    main_key = parts[-1]
    mod_map = {"control": "ctrl", "ctrl": "ctrl", "shift": "shift", "alt": "alt", "meta": "meta", "command": "meta"}
    mods = [mod_map.get(p.lower(), p.lower()) for p in parts[:-1]]
    return main_key, "+".join(mods)


class AgentLimbAPIResponse:
    """兼容 `page.request.get(url)` 返回对象。"""

    def __init__(self, status: int, data: bytes):
        self.status = int(status)
        self.ok = 200 <= self.status < 300
        self._data = data

    def body(self) -> bytes:
        return self._data


class AgentLimbRequestContext:
    """兼容 `page.request.get(url, timeout=...)`（浏览器态带 Cookie fetch，跨域失败时 Python 直拉兜底）。"""

    def __init__(self, page: AgentLimbPage):
        self._page = page

    def get(self, url: str, timeout: int = 60000) -> AgentLimbAPIResponse:
        try:
            b64_data = self._page.evaluate(
                """async (targetUrl) => {
                    const resp = await fetch(targetUrl, { credentials: 'include' });
                    if (!resp.ok) return { errStatus: resp.status };
                    const buf = await resp.arrayBuffer();
                    const bytes = new Uint8Array(buf);
                    let bin = '';
                    const step = 0x8000;
                    for (let i = 0; i < bytes.length; i += step) {
                        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
                    }
                    return { status: resp.status, b64: btoa(bin) };
                }""",
                url,
            )
            if isinstance(b64_data, dict):
                if b64_data.get("errStatus"):
                    return AgentLimbAPIResponse(int(b64_data["errStatus"]), b"")
                if b64_data.get("b64") is not None:
                    raw_bytes = base64.b64decode(b64_data["b64"])
                    return AgentLimbAPIResponse(int(b64_data.get("status") or 200), raw_bytes)
        except Exception:
            pass

        opener = _build_direct_opener()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with opener.open(req, timeout=max(5.0, float(timeout) / 1000.0)) as resp:
                return AgentLimbAPIResponse(int(resp.status), resp.read())
        except urllib.error.HTTPError as exc:
            return AgentLimbAPIResponse(int(exc.code), exc.read())


class AgentLimbDownload:
    """兼容 Playwright `Download` 对象（基于 Chrome 默认下载目录增量捕获）。"""

    def __init__(self, downloaded_path: Path):
        self._path = downloaded_path
        self.suggested_filename = downloaded_path.name

    def save_as(self, destination: str | os.PathLike[str]) -> None:
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.resolve() != self._path.resolve():
            shutil.move(str(self._path), str(dest))


class AgentLimbFileChooser:
    """兼容 Playwright `FileChooser`：通过 DOM DataTransfer 注入避免弹出原生系统文件框。"""

    def __init__(self, page: AgentLimbPage):
        self._page = page

    def set_files(self, files: str | list[str]) -> None:
        paths = [files] if isinstance(files, str) else list(files)
        encoded = []
        for raw_p in paths:
            p = Path(raw_p).expanduser().resolve()
            if p.is_dir():
                raise RuntimeError("AgentLimb 扩展不支持系统目录选择弹窗，请改走 ZIP 兜底上传。")
            mime, _ = mimetypes.guess_type(str(p))
            encoded.append({
                "name": p.name,
                "mime": mime or "application/octet-stream",
                "b64": base64.b64encode(p.read_bytes()).decode("ascii"),
            })
        ok = self._page._eval_raw(
            f"""(() => {{
                const files = {json.dumps(encoded, ensure_ascii=False)};
                const dt = new DataTransfer();
                for (const item of files) {{
                    const bin = atob(item.b64);
                    const arr = new Uint8Array(bin.length);
                    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
                    dt.items.add(new File([arr], item.name, {{ type: item.mime }}));
                }}
                let inp = window.__gwaCapturedFileInput;
                if (!inp) {{
                    const allInputs = Array.from(document.querySelectorAll('input[type="file"]'));
                    inp = allInputs[allInputs.length - 1] || null;
                }}
                if (window.__gwaOrigInputClick) {{
                    HTMLInputElement.prototype.click = window.__gwaOrigInputClick;
                    delete window.__gwaOrigInputClick;
                }}
                delete window.__gwaCapturedFileInput;
                if (!inp) return false;
                try {{ inp.files = dt.files; }} catch (_) {{}}
                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }})()"""
        )
        if not ok:
            raise RuntimeError("未在页面捕获到 <input type='file'>，无法通过 AgentLimb 无弹窗注入文件。")


class AgentLimbLocator:
    """兼容 Playwright `Locator` 常用操作与链式选择。"""

    def __init__(self, page: AgentLimbPage, chain: list[dict]):
        self._page = page
        self._chain = chain

    def locator(self, selector: str) -> AgentLimbLocator:
        return AgentLimbLocator(self._page, [*self._chain, {"selector": selector}])

    def filter(self, has_text: str | re.Pattern | None = None) -> AgentLimbLocator:
        if has_text is None:
            return self
        if isinstance(has_text, re.Pattern):
            flags = "i" if (has_text.flags & re.IGNORECASE) else ""
            step = {"hasTextRegex": has_text.pattern, "hasTextFlags": flags}
        else:
            step = {"hasTextRegex": re.escape(str(has_text)), "hasTextFlags": ""}
        return AgentLimbLocator(self._page, [*self._chain, step])

    @property
    def first(self) -> AgentLimbLocator:
        return self.nth(0)

    @property
    def last(self) -> AgentLimbLocator:
        return self.nth(-1)

    def nth(self, index: int) -> AgentLimbLocator:
        return AgentLimbLocator(self._page, [*self._chain, {"nth": int(index)}])

    def _run_on_target(self, body_js: str, timeout_ms: int = 20000):
        chain_json = json.dumps(self._chain, ensure_ascii=False)
        expr = f"""(() => {{
            {_GWA_DOM_HELPER_JS}
            const els = __gwaResolveChain({chain_json});
            const el = els[0] || null;
            {body_js}
        }})()"""
        return self._page._eval_raw(expr, timeout_ms=timeout_ms)

    def count(self) -> int:
        return int(self._run_on_target("return els.length;") or 0)

    def is_visible(self) -> bool:
        return bool(self._run_on_target("return Boolean(el && __gwaIsVisible(el));"))

    def is_disabled(self) -> bool:
        return bool(
            self._run_on_target(
                "if (!el) return true; return Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true');"
            )
        )

    def inner_text(self) -> str:
        res = self._run_on_target("return el ? __gwaNormText(el) : '';")
        return str(res or "")

    def input_value(self) -> str:
        res = self._run_on_target("return el ? String(el.value ?? '') : '';")
        return str(res or "")

    def get_attribute(self, name: str) -> str | None:
        val = self._run_on_target(f"return el ? el.getAttribute({json.dumps(name)}) : null;")
        return None if val is None else str(val)

    def focus(self) -> None:
        self._run_on_target("if (!el) throw new Error('element not found'); el.focus(); return true;")

    def scroll_into_view_if_needed(self) -> None:
        self._run_on_target("if (el) el.scrollIntoView({ block: 'center', inline: 'nearest' }); return true;")

    def wait_for(self, state: str = "visible", timeout: int = 30000) -> None:
        st = (state or "visible").strip().lower()
        deadline = time.time() + max(0.5, float(timeout) / 1000.0)
        chain_json = json.dumps(self._chain, ensure_ascii=False)
        while time.time() < deadline:
            remaining_ms = int((deadline - time.time()) * 1000)
            slice_ms = max(250, min(8000, remaining_ms))
            expr = f"""(async () => {{
                {_GWA_DOM_HELPER_JS}
                const want = {json.dumps(st)};
                const end = Date.now() + {slice_ms};
                while (true) {{
                    const els = __gwaResolveChain({chain_json});
                    const el = els[0] || null;
                    let ok = false;
                    if (want === 'visible') ok = Boolean(el && __gwaIsVisible(el));
                    else if (want === 'attached') ok = Boolean(el);
                    else if (want === 'hidden' || want === 'detached') ok = !el || (want === 'hidden' && !__gwaIsVisible(el));
                    if (ok) return true;
                    if (Date.now() >= end) return false;
                    await new Promise(r => setTimeout(r, 180));
                }}
            }})()"""
            matched = bool(self._page._eval_raw(expr, timeout_ms=max(10000, slice_ms + 5000)))
            if matched:
                return
        raise TimeoutError(f"AgentLimb wait_for({st}) 超时: {self._chain}")

    def _prepare_point(self) -> dict:
        info = self._run_on_target(
            """if (!el) return { found: false };
            el.scrollIntoView({ block: 'center', inline: 'nearest' });
            const r = el.getBoundingClientRect();
            return {
                found: true,
                cx: r.left + r.width / 2,
                cy: r.top + r.height / 2,
                hasRect: r.width > 0 && r.height > 0,
            };"""
        )
        if not isinstance(info, dict) or not info.get("found"):
            raise RuntimeError(f"目标元素未找到: {self._chain}")
        return info

    def click(self, force_trusted: bool = False) -> None:
        if not force_trusted:
            ok = self._run_on_target(
                """if (!el) return false;
                el.scrollIntoView({ block: 'center', inline: 'nearest' });
                el.click();
                return true;"""
            )
            if ok:
                return
        info = self._prepare_point()
        if info.get("hasRect"):
            try:
                self._page.bridge.call_tool(
                    "computer",
                    {
                        "action": "click",
                        "tabId": self._page.tab_id,
                        "x": round(float(info["cx"]), 1),
                        "y": round(float(info["cy"]), 1),
                    },
                    timeout_ms=20000,
                )
                return
            except Exception:
                pass
        self._run_on_target("if (!el) throw new Error('element not found'); el.click(); return true;")

    def trusted_click(self) -> None:
        """首次按标签页轻触稳态附着 debugger，再通过临时标记 + find 精确 rect + computer(x,y) 完成 isTrusted 点击。"""
        if not getattr(self._page, "_debugger_warmed", False):
            try:
                self._page.bridge.call_tool(
                    "computer",
                    {"action": "hover", "tabId": self._page.tab_id, "x": 1, "y": 1},
                    timeout_ms=3000,
                )
                self._page._debugger_warmed = True
                time.sleep(0.15)
            except Exception:
                pass
        tok = f"gwa_{int(time.time() * 1000)}_{os.getpid()}"
        marked = self._run_on_target(
            f"""if (!el) return false;
            document.querySelectorAll('[data-gwa-target]').forEach(n => n.removeAttribute('data-gwa-target'));
            el.scrollIntoView({{ block: 'center', inline: 'nearest' }});
            el.setAttribute('data-gwa-target', {json.dumps(tok)});
            return true;"""
        )
        if not marked:
            raise RuntimeError(f"目标元素未找到: {self._chain}")
        try:
            fres = self._page.bridge.call_tool(
                "find",
                {"tabId": self._page.tab_id, "selector": f'[data-gwa-target="{tok}"]'},
                timeout_ms=10000,
            )
            matches = []
            if isinstance(fres, dict):
                matches = fres.get("matches") or fres.get("elements") or fres.get("results") or []
            if matches and isinstance(matches[0].get("rect"), dict):
                rect = matches[0]["rect"]
                cx = round(float(rect["x"]) + float(rect["w"]) / 2.0, 1)
                cy = round(float(rect["y"]) + float(rect["h"]) / 2.0, 1)
                self._page.bridge.call_tool(
                    "computer",
                    {"action": "click", "tabId": self._page.tab_id, "x": cx, "y": cy},
                    timeout_ms=10000,
                )
                return
            if matches and matches[0].get("ref") is not None:
                self._page.bridge.call_tool(
                    "computer",
                    {"action": "click", "tabId": self._page.tab_id, "ref": matches[0]["ref"]},
                    timeout_ms=10000,
                )
                return
        except Exception:
            pass
        self.click(force_trusted=True)

    def type_real(self, text: str) -> None:
        """以真实键盘输入文本；若框内有残留草稿先用 JS 安全清空，输入后若未写入再回退 fill。"""
        content = text or ""
        existing = (self.inner_text() or "").strip() or (self.input_value() or "").strip()
        if existing:
            try:
                self.fill("")
            except Exception:
                pass
        self.trusted_click()
        try:
            self.focus()
        except Exception:
            pass
        if content:
            try:
                self._page.bridge.call_tool(
                    "computer",
                    {"action": "type", "tabId": self._page.tab_id, "text": content},
                    timeout_ms=10000,
                )
            except Exception:
                pass
            cur = (self.inner_text() or "").strip() or (self.input_value() or "").strip()
            if not cur:
                self.fill(content)

    def hover(self) -> None:
        info = self._prepare_point()
        if info.get("hasRect"):
            try:
                self._page.bridge.call_tool(
                    "computer",
                    {
                        "action": "hover",
                        "tabId": self._page.tab_id,
                        "x": round(float(info["cx"]), 1),
                        "y": round(float(info["cy"]), 1),
                    },
                    timeout_ms=15000,
                )
                return
            except Exception:
                pass
        self._run_on_target(
            "if (el) el.dispatchEvent(new MouseEvent('mouseover', { bubbles: true })); return true;"
        )

    def fill(self, value: str) -> None:
        val_json = json.dumps(value or "", ensure_ascii=False)
        ok = self._run_on_target(
            f"""if (!el) return false;
            const val = {val_json};
            el.scrollIntoView({{ block: 'center', inline: 'nearest' }});
            el.focus();
            const tag = (el.tagName || '').toUpperCase();
            if (tag === 'TEXTAREA' || tag === 'INPUT') {{
                const proto = tag === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                if (desc && desc.set) desc.set.call(el, val);
                else el.value = val;
                el.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: val }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            try {{
                const sel = window.getSelection();
                const range = document.createRange();
                if ((el.innerText || '').trim()) {{
                    range.selectNodeContents(el);
                    sel.removeAllRanges();
                    sel.addRange(range);
                    document.execCommand('delete');
                }} else {{
                    const anchor = el.querySelector('p') || el;
                    range.selectNodeContents(anchor);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);
                }}
                if (!val || document.execCommand('insertText', false, val)) {{
                    return true;
                }}
            }} catch (_) {{}}
            el.textContent = val;
            el.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: val }}));
            return true;"""
        )
        if not ok:
            raise RuntimeError(f"填充元素失败，未找到目标: {self._chain}")

    def press_sequentially(self, text: str, delay: int = 20) -> None:
        # 避免跨 HTTP 逐字输入造成数十次往返延迟，直接走一次 fill 完成精准文本注入
        self.fill(text)

    def press(self, key: str) -> None:
        self.focus()
        self._page.keyboard.press(key)

    def set_input_files(self, files: str | list[str]) -> None:
        self._run_on_target(
            "if (!el) throw new Error('file input not found'); window.__gwaCapturedFileInput = el; return true;"
        )
        AgentLimbFileChooser(self._page).set_files(files)


class AgentLimbPage:
    """兼容 Playwright `Page` 的轻量代理，底层通过 AgentLimb `/api/tool` 通信。"""

    _is_agentlimb = True

    def __init__(
        self,
        bridge: AgentLimbBridgeClient,
        tab_id: int,
        url: str = "",
        owned: bool = False,
    ):
        self.bridge = bridge
        self.tab_id = int(tab_id)
        self._url = url
        self._url_ts = time.time() if url else 0.0
        self._closed = False
        self._owned = owned
        self.keyboard = AgentLimbKeyboard(self)
        self.request = AgentLimbRequestContext(self)

    @property
    def url(self) -> str:
        if self._closed:
            return self._url
        if not self._url or (time.time() - self._url_ts) > 0.8:
            try:
                res = self.bridge.call_tool("tabs_context", {"tabId": self.tab_id}, timeout_ms=10000)
                if isinstance(res, dict):
                    tabs = res.get("tabs") if isinstance(res.get("tabs"), list) else ([res.get("tab")] if res.get("tab") else [])
                    for t in tabs:
                        if isinstance(t, dict) and int(t.get("id") or -1) == self.tab_id and t.get("url"):
                            self._url = str(t["url"])
                            self._url_ts = time.time()
                            break
            except Exception:
                pass
        return self._url

    def _eval_raw(self, inner_expr: str, timeout_ms: int = 20000):
        wrapped = f"""(async () => {{
            try {{
                const __res = await ({inner_expr});
                return {{ __gwa: 1, ok: true, href: location.href, val: __res === undefined ? null : __res }};
            }} catch (err) {{
                return {{ __gwa: 1, ok: false, href: location.href, error: String((err && err.message) || err) }};
            }}
        }})()"""
        transient_markers = (
            "not an http(s)/file page",
            "cannot access contents",
            "execution context was destroyed",
            "browser disconnected during tool call",
        )
        deadline = time.time() + 18.0
        while True:
            try:
                raw = self.bridge.call_tool(
                    "javascript_eval",
                    {"tabId": self.tab_id, "expression": wrapped},
                    timeout_ms=max(10000, int(timeout_ms)),
                )
                break
            except RuntimeError as exc:
                low = str(exc).lower()
                if time.time() < deadline and any(m in low for m in transient_markers):
                    time.sleep(1.5 if "disconnected" in low else 0.25)
                    continue
                raise
        val, href = _unwrap_eval_payload(raw)
        if href:
            self._url = href
            self._url_ts = time.time()
        return val

    def evaluate(self, expression: str, arg: object = None):
        expr = (expression or "").strip()
        arg_js = json.dumps(arg, ensure_ascii=False) if arg is not None else ""
        wrapped = f"""(async () => {{
            const __target = ({expr});
            const __val = (typeof __target === 'function')
                ? await __target({arg_js})
                : await __target;
            return __val;
        }})()"""
        return self._eval_raw(wrapped, timeout_ms=25000)

    def locator(self, selector: str) -> AgentLimbLocator:
        return AgentLimbLocator(self, [{"selector": selector}])

    def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> None:
        wait_load = (wait_until or "").strip().lower() == "load"
        res = self.bridge.call_tool(
            "navigate",
            {
                "tabId": self.tab_id,
                "url": url,
                "waitForLoad": wait_load,
                "timeout": min(30000, max(5000, int(timeout))),
            },
            timeout_ms=max(15000, int(timeout) + 5000),
        )
        if not wait_load:
            parsed = urllib.parse.urlparse(url)
            needle = (parsed.netloc or "").lower()
            poll_end = time.time() + min(25.0, max(6.0, float(timeout) / 1000.0))
            while time.time() < poll_end:
                cur_u = ""
                try:
                    t_res = self.bridge.call_tool("tabs_context", {"tabId": self.tab_id}, timeout_ms=5000)
                    if isinstance(t_res, dict):
                        tabs = t_res.get("tabs") if isinstance(t_res.get("tabs"), list) else ([t_res.get("tab")] if t_res.get("tab") else [])
                        for t in tabs:
                            if isinstance(t, dict) and int(t.get("id") or -1) == self.tab_id and t.get("url"):
                                cur_u = str(t["url"])
                                break
                except Exception:
                    pass
                if cur_u.startswith(("http://", "https://")) and (not needle or needle in cur_u.lower() or "accounts.google" in cur_u.lower()):
                    self._url = cur_u
                    self._url_ts = time.time()
                    return
                time.sleep(0.3)
        if isinstance(res, dict) and res.get("url"):
            self._url = str(res["url"])
        else:
            self._url = url
        self._url_ts = time.time()

    def bring_to_front(self) -> None:
        self.bridge.call_tool("tab_activate", {"tabId": self.tab_id}, timeout_ms=10000)

    def wait_for_timeout(self, timeout_ms: int) -> None:
        time.sleep(max(0.0, float(timeout_ms) / 1000.0))

    def wait_for_url(self, pattern: str | re.Pattern, timeout: int = 25000) -> None:
        deadline = time.time() + max(0.5, float(timeout) / 1000.0)
        compiled = re.compile(pattern) if isinstance(pattern, str) else pattern
        while time.time() < deadline:
            cur = self.url or ""
            if compiled.search(cur):
                return
            time.sleep(0.35)
        raise TimeoutError(f"等待 URL 匹配 {compiled.pattern} 超时: 当前 {self._url}")

    def is_closed(self) -> bool:
        if self._closed:
            return True
        try:
            res = self.bridge.call_tool("tabs_context", {"tabId": self.tab_id}, timeout_ms=8000)
            if isinstance(res, dict):
                tabs = res.get("tabs")
                if isinstance(tabs, list) and not any(int(t.get("id") or -1) == self.tab_id for t in tabs):
                    self._closed = True
        except Exception:
            pass
        return self._closed

    def close(self) -> None:
        if self._closed:
            return
        try:
            self.bridge.call_tool("tab_close", {"tabId": self.tab_id}, timeout_ms=10000)
        finally:
            self._closed = True

    @contextlib.contextmanager
    def expect_file_chooser(self, timeout: int = 15000):
        # 拦截点击后触发的 <input type="file">.click()，阻止系统文件弹窗抢占焦点
        self._eval_raw(
            """(() => {
                if (!window.__gwaOrigInputClick) {
                    window.__gwaOrigInputClick = HTMLInputElement.prototype.click;
                    HTMLInputElement.prototype.click = function() {
                        if (this && this.type === 'file') {
                            window.__gwaCapturedFileInput = this;
                            return;
                        }
                        return window.__gwaOrigInputClick.apply(this, arguments);
                    };
                }
                return true;
            })()"""
        )

        class _Box:
            value: AgentLimbFileChooser

        box = _Box()
        box.value = AgentLimbFileChooser(self)
        try:
            yield box
        finally:
            try:
                self._eval_raw(
                    """(() => {
                        if (window.__gwaOrigInputClick) {
                            HTMLInputElement.prototype.click = window.__gwaOrigInputClick;
                            delete window.__gwaOrigInputClick;
                        }
                        return true;
                    })()"""
                )
            except Exception:
                pass

    @contextlib.contextmanager
    def expect_download(self, timeout: int = 60000):
        try:
            import platform_utils
            downloads_dir = platform_utils.get_downloads_dir()
        except Exception:
            downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)
        before: dict[str, tuple[int, float]] = {}
        for item in downloads_dir.iterdir():
            if item.is_file():
                try:
                    st = item.stat()
                    before[item.name] = (st.st_size, st.st_mtime)
                except OSError:
                    pass

        class _Box:
            value: AgentLimbDownload

        box = _Box()
        trigger_ts = time.time()
        yield box

        deadline = time.time() + max(5.0, float(timeout) / 1000.0)
        picked: Path | None = None
        while time.time() < deadline:
            cr_downloading = False
            for item in downloads_dir.iterdir():
                if not item.is_file():
                    continue
                low = item.name.lower()
                if low.endswith(".crdownload") or low.endswith(".tmp") or low.endswith(".part"):
                    cr_downloading = True
                    continue
                try:
                    st = item.stat()
                except OSError:
                    continue
                prev = before.get(item.name)
                if prev is None and st.st_size > 0 and st.st_mtime >= (trigger_ts - 2.0):
                    picked = item
                    break
                if prev is not None and st.st_mtime > prev[1] + 0.5 and st.st_size > 0:
                    picked = item
                    break
            if picked is not None and not cr_downloading:
                break
            time.sleep(0.4)
        if picked is None:
            raise TimeoutError(f"在下载目录 {downloads_dir} 等待 Chrome 下载文件超时。")
        box.value = AgentLimbDownload(picked)


class AgentLimbContext:
    """兼容 Playwright `BrowserContext`（基于 AgentLimb 标签页组）。"""

    def __init__(self, browser: AgentLimbBrowser):
        self._browser = browser

    @property
    def pages(self) -> list[AgentLimbPage]:
        res = self._browser.bridge.call_tool("tabs_context", {}, timeout_ms=10000)
        tabs = res.get("tabs") if isinstance(res, dict) and isinstance(res.get("tabs"), list) else []
        out: list[AgentLimbPage] = []
        for tab in tabs:
            if not isinstance(tab, dict) or tab.get("id") is None:
                continue
            tid = int(tab["id"])
            cached = self._browser._page_cache.get(tid)
            if cached and not cached._closed:
                if tab.get("url"):
                    cached._url = str(tab["url"])
                    cached._url_ts = time.time()
                out.append(cached)
            else:
                pg = AgentLimbPage(self._browser.bridge, tid, url=str(tab.get("url") or ""), owned=False)
                self._browser._page_cache[tid] = pg
                out.append(pg)
        return out

    def new_page(self, url: str = "about:blank", active: bool = False) -> AgentLimbPage:
        res = self._browser.bridge.call_tool("tab_new", {"url": url, "active": bool(active)}, timeout_ms=15000)
        tid = None
        init_url = url
        if isinstance(res, dict):
            tid = res.get("tabId") or res.get("id") or (res.get("tab") or {}).get("id")
            init_url = str(res.get("url") or (res.get("tab") or {}).get("url") or url)
        if tid is None:
            raise RuntimeError(f"AgentLimb tab_new 未返回有效 tabId: {res}")
        pg = AgentLimbPage(self._browser.bridge, int(tid), url=init_url, owned=True)
        self._browser._page_cache[int(tid)] = pg
        return pg


class AgentLimbBrowser:
    """兼容 Playwright `Browser` 顶层句柄。"""

    _is_agentlimb = True

    def __init__(self, bridge: AgentLimbBridgeClient, bridge_info: dict | None = None):
        self.bridge = bridge
        self.bridge_info = bridge_info or {}
        self._context = AgentLimbContext(self)
        self._page_cache: dict[int, AgentLimbPage] = {}

    @property
    def contexts(self) -> list[AgentLimbContext]:
        return [self._context]

    def new_context(self) -> AgentLimbContext:
        return self._context

    def is_connected(self) -> bool:
        try:
            res = self.bridge.call_tool("ping", {}, timeout_ms=5000)
            return bool(isinstance(res, dict) and res.get("pong"))
        except Exception:
            return False

    def notify_done(self, summary: str) -> None:
        """结束任务后向 AgentLimb 侧栏发送回复以释放输入框。"""
        try:
            self.bridge.say(summary)
        except Exception:
            pass


def connect_agentlimb_bridge(
    browser_profile: str = "",
    port_override: int | None = None,
) -> AgentLimbBrowser:
    """探测并连接本机运行中的 AgentLimb HTTP Bridge (`/api/tool`)。"""
    info = discover_agentlimb_bridge(port_override=port_override, check_api_tool=True)
    if not info.get("running"):
        raise RuntimeError(
            "未检测到正在运行的 AgentLimb Bridge (127.0.0.1:8765..8780)。"
            "请确认已启用 AgentLimb MCP 且日常 Chrome 扩展已连接。"
        )
    if not info.get("api_tool_supported"):
        raise RuntimeError(
            f"检测到 AgentLimb Bridge (port={info.get('port')})，但未暴露 POST /api/tool 接口（可能是未含本地 RPC 的原版 Host），"
            "请改走 MCP `browser_batch` 通道或使用通道 B (`--setup-ai-chrome --launch-ai-chrome`)。"
        )
    if not info.get("authorized"):
        raise RuntimeError(
            f"AgentLimb Bridge (port={info.get('port')}) 尚未获得 Chrome 授权（stage={info.get('stage')}），"
            "请先在 Chrome 打开 AgentLimb 侧栏点「复制连接提示词」或保持日常 Chrome 窗口开启后重试。"
        )
    client = AgentLimbBridgeClient(
        base_url=str(info["base_url"]),
        browser_profile=browser_profile,
        port=int(info["port"]),
    )
    return AgentLimbBrowser(client, bridge_info=info)
