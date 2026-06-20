"""portable venv — macOS libpython relocatability (public helpers)."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.portable_venv import (
    bundled_python_deps,
    libpython_deps,
    non_portable_libpython_refs,
    non_portable_load_paths,
    non_portable_rpaths,
    relocate_macos_venv,
    _libpython_rpath_deps,
    _stdlib_source_prefix,
    _venv_home_is_local,
)


class PortableVenvMacosTests(unittest.TestCase):
    def test_libpython_deps_filters_dylib(self):
        deps = [
            "/usr/lib/libSystem.B.dylib",
            "/Users/runner/hostedtoolcache/Python/3.10.11/x64/lib/libpython3.10.dylib",
            "@loader_path/../lib/libpython3.10.dylib",
        ]
        self.assertEqual(
            libpython_deps(deps),
            [
                "/Users/runner/hostedtoolcache/Python/3.10.11/x64/lib/libpython3.10.dylib",
                "@loader_path/../lib/libpython3.10.dylib",
            ],
        )

    def test_bundled_python_deps_includes_framework_python(self):
        deps = [
            "/Users/runner/hostedtoolcache/Python/3.10.11/arm64/Python",
            "/usr/lib/libSystem.B.dylib",
        ]
        self.assertEqual(deps[0:1], bundled_python_deps(deps))

    def test_non_portable_load_paths_flags_hostedtoolcache(self):
        deps = [
            "/Users/runner/hostedtoolcache/Python/3.10.11/x64/lib/libpython3.10.dylib",
            "@loader_path/../lib/libpython3.10.dylib",
        ]
        self.assertEqual(
            non_portable_load_paths(deps),
            ["/Users/runner/hostedtoolcache/Python/3.10.11/x64/lib/libpython3.10.dylib"],
        )

    def test_non_portable_libpython_refs_flags_absolute_paths(self):
        deps = [
            "/Users/runner/libpython3.10.dylib",
            "@loader_path/../../libpython3.10.dylib",
            "/usr/lib/libSystem.B.dylib",
        ]
        self.assertEqual(
            non_portable_libpython_refs(deps),
            ["/Users/runner/libpython3.10.dylib"],
        )

    def test_non_portable_rpaths_flags_hostedtoolcache(self):
        self.assertEqual(
            non_portable_rpaths(
                ["/Users/runner/hostedtoolcache/Python/3.10.11/x64/lib"]
            ),
            ["/Users/runner/hostedtoolcache/Python/3.10.11/x64/lib"],
        )

    def test_libpython_rpath_deps_filters_rpath_libpython(self):
        deps = [
            "@rpath/libpython3.10.dylib",
            "@rpath/libfoo.dylib",
            "@loader_path/../lib/libpython3.10.dylib",
        ]
        with patch("scripts.portable_venv._otool_lib_paths", return_value=deps):
            self.assertEqual(
                _libpython_rpath_deps(MagicMock()),
                ["@rpath/libpython3.10.dylib"],
            )

    def test_relocate_macos_venv_is_noop_off_darwin(self):
        with patch("scripts.portable_venv.sys.platform", "linux"):
            relocate_macos_venv(MagicMock())

    def test_venv_home_is_local_under_bundle_bin(self):
        venv = Path("/tmp/canto-0243-portable/venv")
        self.assertTrue(_venv_home_is_local(venv / "bin", venv))
        self.assertFalse(_venv_home_is_local(Path("/install/bin"), venv))

    def test_stdlib_source_prefix_prefers_base_prefix(self):
        cfg = {"base-prefix": "/Library/Frameworks/Python.framework/Versions/3.12"}
        with patch("pathlib.Path.is_dir", return_value=True):
            self.assertEqual(
                _stdlib_source_prefix(cfg, Path("/Library/Frameworks/Python.framework/Versions/3.12/bin")),
                Path("/Library/Frameworks/Python.framework/Versions/3.12"),
            )


if __name__ == "__main__":
    unittest.main()
