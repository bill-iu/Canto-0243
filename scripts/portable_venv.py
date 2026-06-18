#!/usr/bin/env python3
"""Build pre-installed portable venv (--copies) for 免安裝交付."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RUNTIME_SCRIPTS = ("wait_for_url.py", "free_port.py", "local_launch.py")
_LIBPYTHON_RE = re.compile(r"libpython\d+\.\d+\.dylib")
_BUNDLED_LIB = "libpython{major}.{minor}.dylib"


def _bundled_lib_name() -> str:
    return _BUNDLED_LIB.format(major=sys.version_info.major, minor=sys.version_info.minor)


def bundled_python_deps(paths: list[str]) -> list[str]:
    """Public: otool deps that must be bundled for a relocatable macOS venv."""
    out: list[str] = []
    for p in paths:
        if _LIBPYTHON_RE.search(p):
            out.append(p)
        elif p.endswith("/Python") and (
            "Python.framework" in p or "/hostedtoolcache/Python/" in p
        ):
            out.append(p)
    return out


def libpython_deps(paths: list[str]) -> list[str]:
    """Public: libpython dylib deps only (for tests)."""
    return [p for p in paths if _LIBPYTHON_RE.search(p)]


def non_portable_load_paths(paths: list[str], *, venv_root: Path | None = None) -> list[str]:
    """Public: absolute load paths that break off the build machine."""
    venv_prefix = str(venv_root.resolve()) if venv_root else ""
    bad: list[str] = []
    for p in paths:
        if not p.startswith("/"):
            continue
        if venv_prefix and p.startswith(venv_prefix):
            continue
        if p.startswith("/usr/lib") or p.startswith("/System"):
            continue
        if (
            bundled_python_deps([p])
            or "/Users/" in p
            or "hostedtoolcache" in p
            or "Python.framework" in p
        ):
            bad.append(p)
    return bad


def non_portable_libpython_refs(paths: list[str]) -> list[str]:
    """Public: non-portable libpython-style refs (for tests)."""
    return non_portable_load_paths(bundled_python_deps(paths))


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def copy_runtime_scripts(root: Path, repo_root: Path | None = None) -> None:
    repo = repo_root or Path(__file__).resolve().parent.parent
    scripts_dst = root / "scripts"
    scripts_dst.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_SCRIPTS:
        src = repo / "scripts" / name
        if not src.is_file():
            raise FileNotFoundError(f"missing runtime script: {src}")
        shutil.copy2(src, scripts_dst / name)


def _loader_path_ref(from_binary: Path, dylib: Path) -> str:
    rel = os.path.relpath(dylib, start=from_binary.parent).replace("\\", "/")
    return f"@loader_path/{rel}"


def _otool_lib_paths(binary: Path) -> list[str]:
    out = subprocess.check_output(["otool", "-L", str(binary)], text=True)
    paths: list[str] = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        dep = line.split(" (", 1)[0].strip()
        paths.append(dep)
    return paths


def _is_mach_o(path: Path) -> bool:
    try:
        out = subprocess.check_output(["file", "-b", str(path)], text=True)
    except (OSError, subprocess.CalledProcessError):
        return False
    return "Mach-O" in out


def _iter_mach_o_binaries(venv_dir: Path) -> list[Path]:
    roots = [
        venv_dir / "bin",
        venv_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "lib-dynload",
        venv_dir / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages",
    ]
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if _is_mach_o(path):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
    return sorted(seen)


def _bundle_dest(lib_dir: Path, src: Path, dep: str) -> Path:
    dest = lib_dir / src.name
    if dest.is_file() and dest.resolve() != src.resolve():
        digest = hashlib.sha256(dep.encode()).hexdigest()[:8]
        dest = lib_dir / f"{src.name}.{digest}"
    return dest


def relocate_macos_venv(venv_dir: Path) -> None:
    """Bundle non-portable dylibs into venv/lib and rewrite Mach-O paths."""
    if sys.platform != "darwin":
        return

    venv_dir = venv_dir.resolve()
    lib_dir = venv_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)

    for _ in range(8):
        old_to_bundled: dict[str, Path] = {}
        for binary in _iter_mach_o_binaries(venv_dir):
            for dep in non_portable_load_paths(_otool_lib_paths(binary), venv_root=venv_dir):
                if dep in old_to_bundled:
                    continue
                src = Path(dep)
                if not src.is_file():
                    continue
                dest = _bundle_dest(lib_dir, src, dep)
                if not dest.is_file():
                    shutil.copy2(src, dest)
                old_to_bundled[dep] = dest

        if not old_to_bundled:
            break

        for dest in set(old_to_bundled.values()):
            subprocess.run(
                ["install_name_tool", "-id", f"@loader_path/{dest.name}", str(dest)],
                check=True,
                capture_output=True,
            )

        for binary in _iter_mach_o_binaries(venv_dir):
            deps = _otool_lib_paths(binary)
            for old, dest in old_to_bundled.items():
                if old not in deps:
                    continue
                subprocess.run(
                    [
                        "install_name_tool",
                        "-change",
                        old,
                        _loader_path_ref(binary, dest),
                        str(binary),
                    ],
                    check=True,
                    capture_output=True,
                )

    py = _venv_python(venv_dir)
    bad = non_portable_load_paths(_otool_lib_paths(py), venv_root=venv_dir)
    if bad:
        raise RuntimeError(f"python still has non-portable load paths: {bad}")

    _adhoc_sign_venv(venv_dir)


def _adhoc_sign_venv(venv_dir: Path) -> None:
    """Re-sign Mach-O after install_name_tool (ponytail: ad-hoc -, darwin only)."""
    if sys.platform != "darwin":
        return
    signed: set[Path] = set()
    candidates = list(_iter_mach_o_binaries(venv_dir))
    lib_dir = venv_dir / "lib"
    if lib_dir.is_dir():
        for path in lib_dir.iterdir():
            if path.is_file() and _is_mach_o(path):
                candidates.append(path)
    for path in candidates:
        resolved = path.resolve()
        if resolved in signed:
            continue
        signed.add(resolved)
        subprocess.run(
            ["codesign", "--force", "--sign", "-", str(path)],
            check=True,
            capture_output=True,
        )


def assert_portable_macos_venv(venv_dir: Path) -> None:
    if sys.platform != "darwin":
        return
    py = _venv_python(venv_dir)
    bad = non_portable_load_paths(_otool_lib_paths(py), venv_root=venv_dir)
    if bad:
        raise RuntimeError(f"non-portable load paths on {py}: {bad}")


def build_portable_venv(root: Path, *, repo_root: Path | None = None) -> Path:
    """Create root/venv with requirements.txt installed; return python path."""
    root = root.resolve()
    req = root / "requirements.txt"
    if not req.is_file():
        raise FileNotFoundError(f"requirements.txt not found under {root}")

    venv_dir = root / "venv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    subprocess.run(
        [sys.executable, "-m", "venv", "--copies", str(venv_dir)],
        check=True,
    )
    py = _venv_python(venv_dir)
    env = {**os.environ, "PYTHONUTF8": "1"}
    subprocess.run([str(py), "-m", "pip", "install", "-r", str(req)], check=True, env=env)

    relocate_macos_venv(venv_dir)

    py = _venv_python(venv_dir)
    if not py.is_file():
        raise RuntimeError(f"venv python missing after build: {py}")

    copy_runtime_scripts(root, repo_root)
    return py


def main() -> int:
    parser = argparse.ArgumentParser(description="Build portable pre-installed venv")
    parser.add_argument("root", type=Path, help="Portable bundle root (contains requirements.txt)")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Assert venv exists and imports fastapi (ponytail smoke check)",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    if args.self_check:
        py = _venv_python(root / "venv")
        if not py.is_file():
            print(f"FAIL: no venv at {root / 'venv'}", file=sys.stderr)
            return 1
        assert_portable_macos_venv(root / "venv")
        subprocess.run([str(py), "-c", "import fastapi, uvicorn, sqlalchemy"], check=True)
        print("OK")
        return 0

    py = build_portable_venv(root)
    print(f"Portable venv ready: {py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
