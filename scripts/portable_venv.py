#!/usr/bin/env python3
"""Build pre-installed portable venv (--copies) for 免安裝交付."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

RUNTIME_SCRIPTS = ("wait_for_url.py", "free_port.py")


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
        subprocess.run([str(py), "-c", "import fastapi, uvicorn, sqlalchemy"], check=True)
        print("OK")
        return 0

    py = build_portable_venv(root)
    print(f"Portable venv ready: {py}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
