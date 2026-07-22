"""macOS portable 交付 — 隔離清除與全量發佈資產。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ADR-0068 Desktop asset names (legacy portable-* names retired from formal channel)
_MACOS_TAR = {
    "arm64": "canto-0243-desktop-macos-arm64.tar.gz",
    "aarch64": "canto-0243-desktop-macos-arm64.tar.gz",
    "x86_64": "canto-0243-desktop-macos-x86_64.tar.gz",
}


def clear_download_quarantine(
    path: str | Path,
    *,
    platform: str | None = None,
    run=None,
) -> bool:
    """下載隔離標記清除；非 Darwin 為 no-op。"""
    plat = platform if platform is not None else sys.platform
    if plat != "darwin":
        return False
    if run is None:
        run = subprocess.run
    target = str(path)
    # ponytail: -cr clears all xattrs (quarantine, provenance, …); -dr alone misses Sequoia cases
    run(["xattr", "-cr", target], check=False, capture_output=True)
    return True


def patch_portable_venv_cfg(
    bundle_root: str | Path,
    *,
    platform: str | None = None,
) -> bool:
    """Rewrite venv/pyvenv.cfg home to this extract path (build-time paths break off-machine)."""
    root = Path(bundle_root).resolve()
    cfg = root / "venv" / "pyvenv.cfg"
    if not cfg.is_file():
        return False
    plat = platform if platform is not None else sys.platform
    if plat == "win32":
        try:
            from portable_win_runtime import patch_windows_pyvenv_home
        except ImportError:  # pragma: no cover
            from scripts.portable_win_runtime import patch_windows_pyvenv_home

        return patch_windows_pyvenv_home(root)
    venv_bin = (root / "venv" / "bin").resolve()
    lines: list[str] = []
    for line in cfg.read_text().splitlines():
        if line.startswith("home = "):
            lines.append(f"home = {venv_bin}")
        else:
            lines.append(line)
    cfg.write_text("\n".join(lines) + "\n")
    return True


def prepare_portable_bundle(bundle_root: str | Path, *, platform: str | None = None) -> None:
    """Creator launch prep: clear quarantine (macOS) + point venv cfg at this extract folder."""
    root = Path(bundle_root).resolve()
    plat = platform if platform is not None else sys.platform
    clear_download_quarantine(root, platform=plat)
    patch_portable_venv_cfg(root, platform=plat)


def macos_portable_tar_name(machine_arch: str) -> str:
    """依建置機器架構回傳 Desktop macOS tar 檔名（歷史函式名保留）。"""
    name = _MACOS_TAR.get(machine_arch)
    if name is None:
        raise ValueError(f"unsupported macOS build arch: {machine_arch!r}")
    return name


def release_full_macos_artifacts() -> tuple[str, ...]:
    """全量發佈 macOS Desktop 資產（雙原生 tar）。"""
    return (
        macos_portable_tar_name("arm64"),
        macos_portable_tar_name("x86_64"),
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    for path in args:
        prepare_portable_bundle(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
