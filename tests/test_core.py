#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gemini-web-agent 离线回归冒烟测试（纯标准库 unittest，不连接真实浏览器）。"""

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# 允许在未激活 .venv（系统 Python 未安装 playwright）的环境中导入纯逻辑函数
if "playwright" not in sys.modules:
    pw_mod = MagicMock()
    sys.modules["playwright"] = pw_mod
    sys.modules["playwright.sync_api"] = pw_mod.sync_api

import gemini_web as gw  # noqa: E402
import inspect_antigravity as ia  # noqa: E402
import setup_skill as ss  # noqa: E402


class TestGeminiWebCore(unittest.TestCase):
    def test_resolve_ask_entry_defaults_and_auto_chat(self) -> None:
        self.assertEqual(gw._resolve_ask_entry(""), "task")
        self.assertEqual(gw._resolve_ask_entry("", tool="Canvas"), "chat")
        self.assertEqual(gw._resolve_ask_entry("", thinking="高"), "chat")
        self.assertEqual(gw._resolve_ask_entry("chat"), "chat")
        self.assertEqual(gw._resolve_ask_entry("task", tool="Canvas"), "task")

    def test_model_resolution_and_short_name(self) -> None:
        self.assertEqual(gw._resolve_aistudio_model_id("hydrogen"), "gemini-4-hydrogen")
        self.assertEqual(gw._resolve_aistudio_model_id("argon"), "gemini-4-argon")
        self.assertEqual(gw._resolve_aistudio_model_id("lyria"), "lyria-3.5")
        self.assertEqual(gw._resolve_aistudio_model_id("tts"), "gemini-3.8-flash-tts")
        self.assertEqual(
            gw._short_model_name("Gemini 4 Hydrogen gemini-4-hydrogen High speed model for everyday tasks"),
            "gemini-4-hydrogen",
        )
        self.assertTrue(gw._is_media_playground_model("gemini-nano-banana-2.1"))
        self.assertTrue(gw._is_media_playground_model("lyria-3.5"))
        self.assertFalse(gw._is_media_playground_model("gemini-4-hydrogen"))

    def test_cross_platform_devtools_candidates(self) -> None:
        paths = gw._iter_devtools_active_port_files()
        self.assertTrue(len(paths) >= 2)
        self.assertTrue(all(p.name == "DevToolsActivePort" for p in paths))

    def test_write_text_output_and_harvest_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dl_dir = root / "downloads"
            out_dir = root / "project"
            dl_dir.mkdir()

            # 测试 --out-file 直写文件并清空内存字段以省输出 Token
            txt_target = out_dir / "reply.md"
            res = {"status": "ok", "model": "gemini-4-hydrogen", "text": "hello world"}
            written = gw._write_text_output(res, str(txt_target))
            self.assertEqual(written["text"], "")
            self.assertEqual(written["text_chars"], 11)
            self.assertEqual(txt_target.read_text(encoding="utf-8"), "hello world")

            # 测试 harvest 跳过未完成下载，且解包 JSON 到安全相对路径
            (dl_dir / "pending.crdownload").write_text("partial", encoding="utf-8")
            bundle_path = dl_dir / "bundle-vn.json"
            bundle_path.write_text(
                json.dumps({"index.html": "<h1>OK</h1>", "data/story.json": {"title": "Test"}}),
                encoding="utf-8",
            )
            h_res = gw.execute_harvest(
                pattern="bundle*.json",
                dest=str(out_dir),
                src_dir=str(dl_dir),
                since_min=10,
                unpack_json=True,
                copy_only=False,
            )
            self.assertEqual(h_res["status"], "ok")
            self.assertEqual((out_dir / "index.html").read_text(encoding="utf-8"), "<h1>OK</h1>")
            self.assertIn('"title": "Test"', (out_dir / "data" / "story.json").read_text(encoding="utf-8"))
            self.assertFalse(bundle_path.exists())

            # 路径穿越防护校验
            bad_bundle = dl_dir / "bad.json"
            bad_bundle.write_text(json.dumps({"../../escape.txt": "nope"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                gw.execute_harvest(
                    pattern="bad.json",
                    dest=str(out_dir),
                    src_dir=str(dl_dir),
                    since_min=10,
                    unpack_json=True,
                )

    def test_harvest_time_filter_and_copy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dl_dir = root / "downloads"
            out_dir = root / "assets"
            dl_dir.mkdir()
            fresh = dl_dir / "bg.png"
            fresh.write_bytes(b"png")
            old = dl_dir / "old.png"
            old.write_bytes(b"old")
            old_ts = time.time() - 7200
            Path(old).touch()
            import os
            os.utime(old, (old_ts, old_ts))

            h_res = gw.execute_harvest(
                pattern="*.png",
                dest=str(out_dir),
                src_dir=str(dl_dir),
                since_min=5,
                copy_only=True,
            )
            self.assertEqual(h_res["matched_count"], 1)
            self.assertTrue((out_dir / "bg.png").exists())
            self.assertFalse((out_dir / "old.png").exists())
            self.assertTrue(fresh.exists())


class TestSetupAndInspect(unittest.TestCase):
    def test_sync_removes_stale_files_in_subdirs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "skill-dest"
            stale = target / "scripts" / "slice_sprites.py"
            stale.parent.mkdir(parents=True)
            stale.write_text("# stale", encoding="utf-8")
            synced = ss.sync_skill_files(REPO_ROOT, target)
            self.assertTrue(synced)
            self.assertFalse(stale.exists())
            self.assertTrue((target / "references" / "models.md").is_file())
            self.assertTrue((target / "SKILL.md").is_file())

    def test_version_meta_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            ss._write_version_meta(target, REPO_ROOT, commit="abc1234", last_checked_at="2026-11-18T00:00:00+00:00")
            meta = ss._read_version_meta(target)
            self.assertEqual(meta["installed_commit"], "abc1234")
            self.assertTrue(meta["last_checked_at"].startswith("2026-11-18"))

    def test_inspect_render_brief_and_markdown_safe_on_empty(self) -> None:
        empty_report = {"account": {}, "quota_pools": [], "token_analytics": {"today": {}, "all_time": {}, "recent_sessions": []}}
        brief = ia.render_brief_report(empty_report)
        md = ia.render_markdown_report(empty_report)
        self.assertIn("acct=local", brief)
        self.assertIn("today(", brief)
        self.assertTrue(len(md) > 50)


if __name__ == "__main__":
    unittest.main(verbosity=2)
