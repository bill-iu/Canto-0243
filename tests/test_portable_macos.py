"""macOS portable 交付 — 隔離清除與全量發佈資產（公開行為）。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.portable_macos import (
    clear_download_quarantine,
    macos_portable_tar_name,
    patch_portable_venv_cfg,
    prepare_portable_bundle,
    release_full_macos_artifacts,
)


class ClearDownloadQuarantineTests(unittest.TestCase):
    def test_skips_non_darwin(self):
        with patch("scripts.portable_macos.subprocess.run") as run:
            self.assertFalse(clear_download_quarantine("/tmp/x", platform="linux"))
            run.assert_not_called()

    def test_clears_quarantine_on_darwin(self):
        with patch("scripts.portable_macos.subprocess.run") as run:
            self.assertTrue(clear_download_quarantine("/tmp/Canto-0243.app", platform="darwin"))
            run.assert_called_once()
            args = run.call_args[0][0]
            self.assertEqual(args[:2], ["xattr", "-cr"])
            self.assertEqual(args[2], "/tmp/Canto-0243.app")


class ReleaseMacosArtifactsTests(unittest.TestCase):
    def test_dual_arch_tar_names(self):
        names = release_full_macos_artifacts()
        self.assertEqual(
            names,
            (
                "canto-0243-portable-macos-arm64.tar.gz",
                "canto-0243-portable-macos-x86_64.tar.gz",
            ),
        )

    def test_tar_name_from_machine_arch(self):
        self.assertEqual(macos_portable_tar_name("arm64"), "canto-0243-portable-macos-arm64.tar.gz")
        self.assertEqual(macos_portable_tar_name("x86_64"), "canto-0243-portable-macos-x86_64.tar.gz")


class PatchPortableVenvCfgTests(unittest.TestCase):
    def test_rewrites_home_to_extract_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bundle"
            venv_bin = root / "venv" / "bin"
            venv_bin.mkdir(parents=True)
            cfg = root / "venv" / "pyvenv.cfg"
            cfg.write_text("home = /Users/builder/dist/venv/bin\nversion = 3.12.7\n")
            self.assertTrue(patch_portable_venv_cfg(root))
            self.assertIn(f"home = {venv_bin.resolve()}", cfg.read_text())

    def test_prepare_calls_xattr_and_patch(self):
        with patch("scripts.portable_macos.clear_download_quarantine") as clear, patch(
            "scripts.portable_macos.patch_portable_venv_cfg", return_value=True
        ) as patch_cfg:
            prepare_portable_bundle("/tmp/bundle", platform="darwin")
            clear.assert_called_once()
            patch_cfg.assert_called_once()


if __name__ == "__main__":
    unittest.main()
