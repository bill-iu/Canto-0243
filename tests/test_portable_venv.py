"""portable venv — macOS libpython relocatability (public helpers)."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from scripts.portable_venv import (
    libpython_deps,
    non_portable_libpython_refs,
    relocate_macos_venv,
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

    def test_relocate_macos_venv_is_noop_off_darwin(self):
        with patch("scripts.portable_venv.sys.platform", "linux"):
            relocate_macos_venv(MagicMock())


if __name__ == "__main__":
    unittest.main()
