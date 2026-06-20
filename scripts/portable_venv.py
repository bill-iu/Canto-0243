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


def _otool_rpaths(binary: Path) -> list[str]:
    out = subprocess.check_output(["otool", "-l", str(binary)], text=True)
    paths: list[str] = []
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if "cmd LC_RPATH" not in line:
            continue
        for follow in lines[i + 1 : i + 5]:
            match = re.search(r"path\s+(.+?)\s*(?:\(offset|\(align|$)", follow.strip())
            if match:
                paths.append(match.group(1).strip())
                break
    return paths


def non_portable_rpaths(paths: list[str], *, venv_root: Path | None = None) -> list[str]:
    """Public: LC_RPATH entries that break off the build machine."""
    return [p for p in paths if non_portable_load_paths([p], venv_root=venv_root)]


def _delete_non_portable_rpaths(binary: Path, venv_dir: Path) -> None:
    for _ in range(8):
        bad = non_portable_rpaths(_otool_rpaths(binary), venv_root=venv_dir)
        if not bad:
            return
        for rpath in bad:
            subprocess.run(
                ["install_name_tool", "-delete_rpath", rpath, str(binary)],
                check=True,
                capture_output=True,
            )


def _rpath_fixup_binaries(venv_dir: Path) -> list[Path]:
    """Mach-O that may reference libpython via @rpath (not every site-packages .so)."""
    py = _venv_python(venv_dir)
    bins: list[Path] = [py]
    bin_dir = venv_dir / "bin"
    if bin_dir.is_dir():
        bins.extend(p for p in bin_dir.iterdir() if p.is_file() and _is_mach_o(p))
    seen: set[Path] = set()
    out: list[Path] = []
    for binary in bins:
        resolved = binary.resolve()
        if resolved not in seen:
            seen.add(resolved)
            out.append(binary)
    return out


def _libpython_rpath_deps(binary: Path) -> list[str]:
    return [
        dep
        for dep in _otool_lib_paths(binary)
        if dep.startswith("@rpath/") and _LIBPYTHON_RE.search(dep)
    ]


def _fix_rpath_and_loader_deps(binary: Path, lib_dir: Path) -> None:
    bundled = lib_dir / _bundled_lib_name()
    if not bundled.is_file():
        return
    rpath_deps = _libpython_rpath_deps(binary)
    if not rpath_deps:
        return
    rel_lib = os.path.relpath(lib_dir, start=binary.parent).replace("\\", "/")
    loader_lib = f"@loader_path/{rel_lib}"
    if loader_lib not in _otool_rpaths(binary):
        proc = subprocess.run(
            ["install_name_tool", "-add_rpath", loader_lib, str(binary)],
            capture_output=True,
        )
        if proc.returncode != 0 and b"duplicate" not in proc.stderr.lower():
            proc.check_returncode()
    for dep in rpath_deps:
        tail = dep.removeprefix("@rpath/")
        target = lib_dir / tail
        if not target.is_file():
            target = bundled
        subprocess.run(
            [
                "install_name_tool",
                "-change",
                dep,
                _loader_path_ref(binary, target),
                str(binary),
            ],
            check=True,
            capture_output=True,
        )


def _bundle_dest(lib_dir: Path, src: Path, dep: str) -> Path:
    dest = lib_dir / src.name
    if dest.is_file() and dest.resolve() != src.resolve():
        digest = hashlib.sha256(dep.encode()).hexdigest()[:8]
        dest = lib_dir / f"{src.name}.{digest}"
    return dest


def _bundle_dep(lib_dir: Path, dep: str) -> Path | None:
    src = Path(dep)
    if not src.is_file():
        return None

    cursor = src
    while cursor.parent != cursor:
        if cursor.name == "Resources" and (cursor / "Python.app").is_dir():
            dest_root = lib_dir / "Resources"
            shutil.copytree(cursor, dest_root, dirs_exist_ok=True)
            return dest_root / src.relative_to(cursor)
        cursor = cursor.parent

    dest = _bundle_dest(lib_dir, src, dep)
    if not dest.is_file() or dest.resolve() != src.resolve():
        shutil.copy2(src, dest)
    return dest


def _seed_venv_libpython(venv_dir: Path) -> None:
    """Copy libpython into venv/lib when --copies leaves an @executable_path ref unfilled."""
    if sys.platform != "darwin":
        return
    lib_dir = venv_dir / "lib"
    bundled = lib_dir / _bundled_lib_name()
    if bundled.is_file():
        return
    py = _venv_python(venv_dir)
    want = f"@executable_path/../lib/{bundled.name}"
    if want not in _otool_lib_paths(py):
        return
    for src in (
        Path(sys.base_prefix) / "lib" / bundled.name,
        Path(sys.executable).resolve().parent.parent / "lib" / bundled.name,
    ):
        if src.is_file():
            lib_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, bundled)
            return


def _parse_pyvenv_cfg(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        if " = " not in line:
            continue
        key, value = line.split(" = ", 1)
        out[key.strip()] = value.strip()
    return out


def _venv_home_is_local(home: Path, venv_dir: Path) -> bool:
    try:
        home.resolve().relative_to((venv_dir / "bin").resolve())
        return True
    except ValueError:
        return False


def _stdlib_source_prefix(cfg: dict[str, str], home: Path) -> Path | None:
    base = cfg.get("base-prefix")
    if base:
        candidate = Path(base)
        if candidate.is_dir():
            return candidate
    parent = home.parent
    return parent if parent.is_dir() else None


def _materialize_portable_stdlib(venv_dir: Path) -> None:
    """Embed build-time stdlib in venv so 免安裝 bundle runs off any extract path."""
    if sys.platform != "darwin":
        return
    cfg_path = venv_dir / "pyvenv.cfg"
    if not cfg_path.is_file():
        return
    text = cfg_path.read_text()
    cfg = _parse_pyvenv_cfg(text)
    home_raw = cfg.get("home")
    if not home_raw:
        return
    home = Path(home_raw)
    if _venv_home_is_local(home, venv_dir):
        return
    src_prefix = _stdlib_source_prefix(cfg, home)
    if src_prefix is None:
        raise RuntimeError(f"cannot locate stdlib source for portable venv: {cfg_path}")

    ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
    src_lib = src_prefix / "lib" / ver
    dst_lib = venv_dir / "lib" / ver
    if src_lib.is_dir():
        shutil.copytree(src_lib, dst_lib, dirs_exist_ok=True)

    zip_name = f"python{sys.version_info.major}{sys.version_info.minor}.zip"
    src_zip = src_prefix / "lib" / zip_name
    if src_zip.is_file():
        dst_zip = venv_dir / "lib" / zip_name
        if not dst_zip.is_file():
            shutil.copy2(src_zip, dst_zip)

    bundled_src = src_prefix / "lib" / _bundled_lib_name()
    if bundled_src.is_file():
        lib_dir = venv_dir / "lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        bundled = lib_dir / _bundled_lib_name()
        if not bundled.is_file():
            shutil.copy2(bundled_src, bundled)

    venv_home = (venv_dir / "bin").resolve()
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("home = "):
            lines.append(f"home = {venv_home}")
        else:
            lines.append(line)
    cfg_path.write_text("\n".join(lines) + "\n")


def _assert_venv_relocatable(venv_dir: Path) -> None:
    """Fail build if venv python still resolves stdlib outside the bundle."""
    py = _venv_python(venv_dir)
    root = str(venv_dir.resolve())
    code = f"""import sys
root = {root!r}
if not sys.prefix.startswith(root):
    raise SystemExit(f"prefix {{sys.prefix!r}} not under {{root!r}}")
for entry in sys.path:
    if not entry or entry.startswith(root):
        continue
    if entry.startswith("/usr") or entry.startswith("/System"):
        continue
    if entry.startswith("/"):
        raise SystemExit(f"non-portable sys.path entry: {{entry!r}}")
"""
    proc = subprocess.run([str(py), "-c", code], capture_output=True, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"venv not relocatable: {detail}")


def _ensure_venv_pip(py: Path) -> None:
    if subprocess.run([str(py), "-m", "pip", "--version"], capture_output=True).returncode == 0:
        return
    subprocess.run([str(py), "-m", "ensurepip", "--upgrade", "--default-pip"], check=True)


def _create_copies_venv(venv_dir: Path) -> None:
    """Create a relocatable venv (file copies, not symlinks to system Python)."""
    last: subprocess.CompletedProcess[str] | None = None
    for extra in ((), ("--without-pip",)):
        if venv_dir.exists():
            shutil.rmtree(venv_dir)
        proc = subprocess.run(
            [sys.executable, "-m", "venv", "--copies", *extra, str(venv_dir)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return
        last = proc
    err = ((last.stderr or "") + (last.stdout or "")) if last else ""
    if "cannot create venvs without using symlinks" not in err:
        raise subprocess.CalledProcessError(
            last.returncode if last else 1,
            last.args if last else [],
            last.stdout if last else "",
            last.stderr if last else "",
        )
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "virtualenv"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, "-m", "virtualenv", "--always-copy", str(venv_dir)],
        check=True,
    )


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
                dest = _bundle_dep(lib_dir, dep)
                if dest is None:
                    continue
                old_to_bundled[dep] = dest

        if not old_to_bundled:
            break

        for dest in set(old_to_bundled.values()):
            if dest.parent != lib_dir:
                continue
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
    bundled = lib_dir / _bundled_lib_name()
    if not bundled.is_file():
        for dep in non_portable_load_paths(_otool_lib_paths(py)):
            dest = _bundle_dep(lib_dir, dep)
            if dest is not None and bundled.is_file():
                break
        if not bundled.is_file():
            for rpath in _otool_rpaths(py):
                candidate = Path(rpath) / bundled.name
                if candidate.is_file():
                    shutil.copy2(candidate, bundled)
                    break
    if not bundled.is_file():
        raise RuntimeError(f"could not bundle {bundled.name} for portable venv")

    for binary in _iter_mach_o_binaries(venv_dir):
        _delete_non_portable_rpaths(binary, venv_dir)
    for binary in _rpath_fixup_binaries(venv_dir):
        _fix_rpath_and_loader_deps(binary, lib_dir)

    dot_ref = "@executable_path/../.Python"
    for binary in _iter_mach_o_binaries(venv_dir):
        if dot_ref in _otool_lib_paths(binary):
            subprocess.run(
                [
                    "install_name_tool",
                    "-change",
                    dot_ref,
                    _loader_path_ref(binary, bundled),
                    str(binary),
                ],
                check=True,
                capture_output=True,
            )

    _assert_venv_portable(venv_dir)
    _adhoc_sign_venv(venv_dir)


def _assert_venv_portable(venv_dir: Path) -> None:
    py = _venv_python(venv_dir)
    bad = non_portable_load_paths(_otool_lib_paths(py), venv_root=venv_dir)
    bad_rpaths = non_portable_rpaths(_otool_rpaths(py), venv_root=venv_dir)
    if bad or bad_rpaths:
        raise RuntimeError(
            f"non-portable python load paths={bad} rpaths={bad_rpaths}"
        )


def _iter_all_mach_o_under(root: Path) -> list[Path]:
    seen: set[Path] = set()
    if not root.is_dir():
        return []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink() and _is_mach_o(path):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
    return sorted(seen)


def _adhoc_sign_venv(venv_dir: Path) -> None:
    """Re-sign every Mach-O in venv after install_name_tool (ponytail: ad-hoc -, darwin only)."""
    if sys.platform != "darwin":
        return
    for path in _iter_all_mach_o_under(venv_dir):
        subprocess.run(
            ["codesign", "--force", "--sign", "-", str(path)],
            check=True,
            capture_output=True,
        )


def assert_portable_macos_venv(venv_dir: Path) -> None:
    if sys.platform != "darwin":
        return
    _assert_venv_portable(venv_dir)


def build_portable_venv(root: Path, *, repo_root: Path | None = None) -> Path:
    """Create root/venv with requirements.txt installed; return python path."""
    root = root.resolve()
    req = root / "requirements.txt"
    if not req.is_file():
        raise FileNotFoundError(f"requirements.txt not found under {root}")

    venv_dir = root / "venv"
    if venv_dir.exists():
        shutil.rmtree(venv_dir)

    _create_copies_venv(venv_dir)
    _seed_venv_libpython(venv_dir)
    _materialize_portable_stdlib(venv_dir)
    py = _venv_python(venv_dir)
    _ensure_venv_pip(py)
    env = {**os.environ, "PYTHONUTF8": "1"}
    subprocess.run([str(py), "-m", "pip", "install", "-r", str(req)], check=True, env=env)

    relocate_macos_venv(venv_dir)
    _assert_venv_relocatable(venv_dir)

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
        _assert_venv_relocatable(root / "venv")
        subprocess.run([str(py), "-c", "import fastapi, uvicorn, sqlalchemy"], check=True)
        print("OK")
        return 0

    py = build_portable_venv(root)
    print(f"Portable venv ready: {py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
