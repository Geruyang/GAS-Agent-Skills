"""Regression tests for contributor maintenance commands; writes use temporary fixtures."""

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock


PACKAGE = Path(__file__).absolute().parents[1]
SCRIPTS = PACKAGE / "scripts"
spec = importlib.util.spec_from_file_location("gas_maintenance_manifest", SCRIPTS / "update_manifest.py")
manifest_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest_tool)


class MaintenanceToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.root = self.folder / "package"
        self.root.mkdir()
        (self.root / "a.txt").write_bytes(b"original")

    def cli(self, script="update_manifest.py", *args, code=0, root=None):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / script), "--root",
                                 str(root or self.root), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.root.rglob("*") if p.is_file()}

    def create_shared(self):
        self.names = ("gas-centralized-development", "gas-decentralized-development", "gas-combined-development")
        for name in self.names:
            base = self.root / name
            (base / "scripts").mkdir(parents=True)
            (base / "references").mkdir()
            (base / "SKILL.md").write_text("## 子 Agent 创建前的人类交互（AGENT-01）\n\nSame rules\n\n## 权责边界\n" + name,
                                           encoding="utf-8")
            for rel in ("scripts/gas_runtime.py", "references/runtime-evidence.md", "references/research-basis.md"):
                (base / rel).write_bytes(("canonical " + rel).encode())

    def real_symlink(self, link, target, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("Host cannot create symlinks: " + str(exc))
        if not stat.S_ISLNK(link.lstat().st_mode):
            if link.is_file():
                link.unlink()
            self.skipTest("Host did not create a real symlink")
        self.addCleanup(link.unlink)

    def test_default_and_explicit_checks_do_not_write(self):
        before = self.snapshot()
        self.cli(code=1)
        self.cli("update_manifest.py", "--check", code=1)
        self.assertEqual(self.snapshot(), before)
        self.cli("update_manifest.py", "--write")
        before = self.snapshot()
        self.cli()
        self.cli("update_manifest.py", "--check")
        self.cli("update_manifest.py", "--write")
        self.assertEqual(self.snapshot(), before)

    def test_tamper_addition_removal_reported_before_explicit_write(self):
        self.cli("update_manifest.py", "--write")
        saved = (self.root / "manifest.sha256.json").read_bytes()
        (self.root / "a.txt").write_bytes(b"tampered")
        (self.root / "new.txt").write_bytes(b"new")
        result = self.cli(code=1)
        self.assertIn("changed: a.txt", result.stdout)
        self.assertIn("added: new.txt", result.stdout)
        self.assertEqual((self.root / "manifest.sha256.json").read_bytes(), saved)
        self.cli("update_manifest.py", "--write")
        self.cli()
        (self.root / "new.txt").unlink()
        self.assertIn("removed: new.txt", self.cli(code=1).stdout)

    def test_sorted_posix_hashes_exclusions_and_no_temporary_self_index(self):
        (self.root / "z").mkdir()
        (self.root / "z" / "B.txt").write_bytes(b"nested")
        (self.root / "z" / "manifest.sha256.json").write_text("ignored", encoding="utf-8")
        (self.root / "__pycache__").mkdir()
        (self.root / "__pycache__" / "cache.pyc").write_bytes(b"ignored")
        self.cli("update_manifest.py", "--write")
        manifest = json.loads((self.root / "manifest.sha256.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest, {"version": 1, "algorithm": "sha256", "files": {
            "a.txt": hashlib.sha256(b"original").hexdigest(), "z/B.txt": hashlib.sha256(b"nested").hexdigest()}})
        self.assertEqual(list(manifest["files"]), sorted(manifest["files"]))
        self.assertEqual(list(self.root.glob(".gas-maintenance-*")), [])
        self.cli()

    def test_malformed_manifest_requires_explicit_write(self):
        target = self.root / "manifest.sha256.json"
        target.write_text('{"files": {}, "files": {}}', encoding="utf-8")
        result = self.cli(code=1)
        self.assertIn("Duplicate manifest key", result.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), '{"files": {}, "files": {}}')
        self.cli("update_manifest.py", "--write")
        self.cli()

    def test_write_modes_are_mutually_exclusive(self):
        self.cli("update_manifest.py", "--check", "--write", code=2)
        self.cli("sync_shared_assets.py", "--check", "--write", code=2)

    def test_gbk_output_for_emoji_paths_preserves_success_and_error_receipts(self):
        emoji_root = self.folder / "package-\U0001f680"
        self.root.rename(emoji_root)
        self.root = emoji_root
        (self.root / "file-\U0001f680.txt").write_bytes(b"unicode path")
        env = dict(os.environ, PYTHONIOENCODING="gbk:strict")

        def run(script, *args):
            return subprocess.run([sys.executable, "-B", str(SCRIPTS / script), "--root",
                                   str(self.root), *args], capture_output=True, text=True,
                                  encoding="gbk", env=env)

        written = run("update_manifest.py", "--write")
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        self.assertIn("Updated ", written.stdout)
        self.assertIn("package-\\U0001f680", written.stdout)
        self.assertIn("file-\\U0001f680.txt", written.stdout)
        self.assertTrue((self.root / "manifest.sha256.json").is_file())
        checked = run("update_manifest.py", "--check")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        missing = run("sync_shared_assets.py", "--check")
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertIn("ERROR:", missing.stderr)
        self.assertIn("package-\\U0001f680", missing.stderr)
        self.assertNotIn("Traceback", missing.stderr)
        self.create_shared()
        synchronized = run("sync_shared_assets.py", "--write")
        self.assertEqual(synchronized.returncode, 0, synchronized.stdout + synchronized.stderr)

    def test_output_configuration_accepts_streams_without_reconfigure(self):
        with mock.patch.object(manifest_tool.sys, "stdout", object()), \
                mock.patch.object(manifest_tool.sys, "stderr", object()):
            manifest_tool.configure_output()

    def test_shared_default_check_and_explicit_sync(self):
        self.create_shared()
        self.cli("sync_shared_assets.py")
        target = self.root / self.names[1] / "scripts/gas_runtime.py"
        target.write_bytes(b"drift")
        missing = self.root / self.names[2] / "references/research-basis.md"
        missing.unlink()
        before = self.snapshot()
        self.cli("sync_shared_assets.py", code=1)
        self.cli("sync_shared_assets.py", "--check", code=1)
        self.assertEqual(self.snapshot(), before)
        self.cli("sync_shared_assets.py", "--write")
        self.assertEqual(target.read_bytes(), (self.root / self.names[0] / "scripts/gas_runtime.py").read_bytes())
        self.assertTrue(missing.is_file())
        before = self.snapshot()
        self.cli("sync_shared_assets.py")
        self.cli("sync_shared_assets.py", "--write")
        self.assertEqual(self.snapshot(), before)

    def test_agent_section_drift_stops_write_and_is_not_automatically_rewritten(self):
        self.create_shared()
        skill = self.root / self.names[2] / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8").replace("Same rules", "Different rules"), encoding="utf-8")
        (self.root / self.names[1] / "scripts/gas_runtime.py").write_bytes(b"drift")
        before = self.snapshot()
        self.assertIn("AGENT-01 differs", self.cli("sync_shared_assets.py", "--write", code=1).stderr)
        self.assertEqual(self.snapshot(), before)

    def test_missing_agent_section_is_actionable_error(self):
        self.create_shared()
        (self.root / self.names[0] / "SKILL.md").write_text("No heading", encoding="utf-8")
        self.assertIn("section boundaries", self.cli("sync_shared_assets.py", code=2).stderr)

    def test_shared_check_without_python_B_creates_no_cache(self):
        self.create_shared()
        scripts = self.root / "scripts"
        scripts.mkdir()
        for name in ("update_manifest.py", "sync_shared_assets.py"):
            shutil.copyfile(SCRIPTS / name, scripts / name)
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(scripts / "sync_shared_assets.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((scripts / "__pycache__").exists())
        self.assertEqual(self.snapshot(), before)

    def test_manifest_default_root_is_script_parent_package(self):
        scripts = self.root / "scripts"
        scripts.mkdir()
        shutil.copyfile(SCRIPTS / "update_manifest.py", scripts / "update_manifest.py")
        result = subprocess.run([sys.executable, "-B", str(scripts / "update_manifest.py")],
                                cwd=str(self.folder), capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("added: a.txt", result.stdout)
        self.assertIn("added: scripts/update_manifest.py", result.stdout)

    def test_symlink_file_is_rejected_even_with_write(self):
        outside = self.folder / "outside.txt"
        outside.write_bytes(b"outside")
        self.real_symlink(self.root / "alias.txt", outside)
        self.assertIn("symlink/reparse", self.cli("update_manifest.py", "--write", code=2).stderr)
        self.assertFalse((self.root / "manifest.sha256.json").exists())

    def test_manifest_symlink_is_rejected(self):
        outside = self.folder / "outside.json"
        outside.write_text("{}", encoding="utf-8")
        self.real_symlink(self.root / "manifest.sha256.json", outside)
        self.cli("update_manifest.py", "--write", code=2)
        self.assertEqual(outside.read_text(encoding="utf-8"), "{}")

    def test_root_symlink_and_symlink_ancestor_are_rejected(self):
        alias = self.folder / "alias"
        self.real_symlink(alias, self.root, directory=True)
        (self.root / "child").mkdir()
        for root in (alias, alias / "child"):
            self.cli(root=root, code=2)
            self.cli("sync_shared_assets.py", root=root, code=2)

    def test_shared_symlink_destination_rejected_before_any_write(self):
        self.create_shared()
        target = self.root / self.names[2] / "references/research-basis.md"
        target.unlink()
        outside = self.folder / "outside.txt"
        outside.write_bytes(b"outside")
        self.real_symlink(target, outside)
        drift = self.root / self.names[1] / "scripts/gas_runtime.py"
        drift.write_bytes(b"drift")
        self.cli("sync_shared_assets.py", "--write", code=2)
        self.assertEqual(drift.read_bytes(), b"drift")
        self.assertEqual(outside.read_bytes(), b"outside")

    def test_reparse_attribute_rejected_before_file_read(self):
        original = Path.lstat
        target = self.root / "a.txt"

        def fake_lstat(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400) if path == target else info

        with mock.patch.object(Path, "lstat", fake_lstat), mock.patch.object(manifest_tool, "read_regular") as read:
            with self.assertRaisesRegex(ValueError, "symlink/reparse"):
                manifest_tool.package_manifest(self.root)
            read.assert_not_called()

    def test_atomic_replace_failure_preserves_original_and_cleans_temp_file(self):
        target = self.root / "a.txt"
        with mock.patch.object(manifest_tool.os, "replace", side_effect=OSError("replace denied")):
            with self.assertRaisesRegex(OSError, "replace denied"):
                manifest_tool.atomic_write(target, b"replacement")
        self.assertEqual(target.read_bytes(), b"original")
        self.assertEqual(list(self.root.glob(".gas-maintenance-*")), [])

    @unittest.skipUnless(os.name == "nt", "Windows junction fixture")
    def test_windows_junction_is_rejected(self):
        outside = self.folder / "outside"
        outside.mkdir()
        (outside / "private.txt").write_bytes(b"outside")
        junction = self.root / "junction"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            self.skipTest("Host cannot create junctions: " + result.stderr)
        self.addCleanup(os.rmdir, str(junction))
        self.assertTrue(getattr(junction.lstat(), "st_file_attributes", 0) & 0x400)
        self.cli("update_manifest.py", "--write", code=2)
        self.cli(root=junction, code=2)
        (outside / "child").mkdir()
        self.cli(root=junction / "child", code=2)
        self.cli("sync_shared_assets.py", root=junction / "child", code=2)
        self.assertEqual((outside / "private.txt").read_bytes(), b"outside")

    @unittest.skipUnless(os.name == "nt", "Windows junction fixture")
    def test_shared_junction_destination_rejected_before_any_write(self):
        self.create_shared()
        peer = self.root / self.names[2]
        outside = self.folder / "outside-references"
        (peer / "references").rename(outside)
        junction = peer / "references"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            self.skipTest("Host cannot create junctions: " + result.stderr)
        self.addCleanup(os.rmdir, str(junction))
        self.assertTrue(getattr(junction.lstat(), "st_file_attributes", 0) & 0x400)
        drift = self.root / self.names[1] / "scripts/gas_runtime.py"
        drift.write_bytes(b"drift")
        self.cli("sync_shared_assets.py", "--write", code=2)
        self.assertEqual(drift.read_bytes(), b"drift")
        self.assertEqual((outside / "runtime-evidence.md").read_bytes(), b"canonical references/runtime-evidence.md")

    def test_python_39_syntax(self):
        for name in ("update_manifest.py", "sync_shared_assets.py"):
            ast.parse((SCRIPTS / name).read_text(encoding="utf-8"), feature_version=(3, 9))


if __name__ == "__main__":
    unittest.main()
