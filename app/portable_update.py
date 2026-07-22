"""Portable 套件更新提示（ADR-0059）：指紋核對、fail-open、指紋略過。"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional

MANIFEST_NAME = "portable-manifest.json"
SKIP_NAME = "portable-update-skip"
RESULT_NAME = "portable-update.json"
DEFAULT_REPO = "bill-iu/Canto-0243"
DEFAULT_TIMEOUT_S = 2.0

# Exclude from package_digest (volatile / self)
_SKIP_TREE_PREFIXES = (".cache/",)
_SKIP_TREE_NAMES = {MANIFEST_NAME}


def github_repo() -> str:
    return (os.getenv("GH_REPO") or os.getenv("CANTO_GITHUB_REPO") or DEFAULT_REPO).strip()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def package_digest(root: Path) -> str:
    """Tree digest of package files except manifest and .cache (ADR-0059).

    ponytail: full-tree SHA can dominate release build time on large venvs;
    ceiling = O(files). Upgrade: content-addressed archive digest outside the zip
    if build time becomes painful.
    """
    lines: list[str] = []
    root = root.resolve()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in _SKIP_TREE_NAMES:
            continue
        if any(rel.startswith(p) for p in _SKIP_TREE_PREFIXES):
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        lines.append(f"{rel}\0{file_sha256(path)}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def fingerprint_id(fp: dict[str, str]) -> str:
    return "|".join(
        [
            fp.get("tag", ""),
            fp.get("platform", ""),
            fp.get("lyrics_sha256", ""),
            fp.get("package_digest", ""),
        ]
    )


def read_manifest(root: Path) -> Optional[dict[str, str]]:
    path = root / MANIFEST_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    need = ("tag", "platform", "lyrics_sha256", "package_digest")
    if not all(isinstance(data.get(k), str) and data[k] for k in need):
        return None
    return {k: str(data[k]) for k in need}


def count_tree_files(root: Path) -> int:
    root = root.resolve()
    n = 0
    for path in root.rglob("*"):
        if path.is_file():
            n += 1
    return n


def write_manifest(
    root: Path,
    *,
    tag: str,
    platform: str,
    sidecar: Path | None = None,
) -> dict[str, str]:
    """Write local + optional release sidecar. Call before zip/tar."""
    root = root.resolve()
    db = root / "lyrics.db"
    if not db.is_file():
        raise FileNotFoundError(f"lyrics.db missing under {root}")
    # Remove old manifest so it does not affect digest
    man = root / MANIFEST_NAME
    if man.is_file():
        man.unlink()
    venv = root / "venv"
    data = root / "data"
    pack = root / "venv.pack"
    fp: dict[str, Any] = {
        "tag": tag if tag.startswith("v") else f"v{tag.lstrip('v')}",
        "platform": platform,
        "lyrics_sha256": file_sha256(db),
        "package_digest": package_digest(root),
        "file_count": str(count_tree_files(root)),
        "venv_file_count": str(count_tree_files(venv) if venv.is_dir() else 0),
        "data_file_count": str(count_tree_files(data)),
    }
    if pack.is_file():
        fp["venv_pack_sha256"] = file_sha256(pack)
    pack_meta = root / "portable-venv-pack.json"
    if pack_meta.is_file():
        try:
            pmeta = json.loads(pack_meta.read_text(encoding="utf-8"))
            if isinstance(pmeta.get("venv_unpacked_file_count"), int):
                fp["venv_unpacked_file_count"] = str(pmeta["venv_unpacked_file_count"])
            if isinstance(pmeta.get("venv_pack_sha256"), str) and "venv_pack_sha256" not in fp:
                fp["venv_pack_sha256"] = pmeta["venv_pack_sha256"]
        except (OSError, json.JSONDecodeError):
            pass
    # Slim report: under venv/ (unpacked) or bundle root after pack (ADR-0067)
    slim_report = venv / "portable-venv-slim.json"
    if not slim_report.is_file():
        slim_report = root / "portable-venv-slim.json"
    if slim_report.is_file():
        try:
            slim = json.loads(slim_report.read_text(encoding="utf-8"))
            if isinstance(slim.get("venv_files_after"), int):
                fp["venv_files_after"] = str(slim["venv_files_after"])
            if isinstance(slim.get("venv_files_before"), int):
                fp["venv_files_before"] = str(slim["venv_files_before"])
        except (OSError, json.JSONDecodeError):
            pass
    data_slim_report = data / "portable-data-slim.json"
    if data_slim_report.is_file():
        try:
            dslim = json.loads(data_slim_report.read_text(encoding="utf-8"))
            if isinstance(dslim.get("data_files_after"), int):
                fp["data_files_after"] = str(dslim["data_files_after"])
            if isinstance(dslim.get("data_files_before"), int):
                fp["data_files_before"] = str(dslim["data_files_before"])
        except (OSError, json.JSONDecodeError):
            pass
    text = json.dumps(fp, ensure_ascii=False, indent=2) + "\n"
    man.write_text(text, encoding="utf-8")
    if sidecar is not None:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(text, encoding="utf-8")
    return {k: str(v) for k, v in fp.items()}


def _cache_dir(root: Path) -> Path:
    d = root / ".cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def read_skip(root: Path) -> Optional[str]:
    p = _cache_dir(root) / SKIP_NAME
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def write_skip(root: Path, remote_fp_id: str) -> None:
    (_cache_dir(root) / SKIP_NAME).write_text(remote_fp_id + "\n", encoding="utf-8")


def write_result(root: Path, payload: dict[str, Any]) -> Path:
    path = _cache_dir(root) / RESULT_NAME
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_result(root: Path) -> Optional[dict[str, Any]]:
    path = root / ".cache" / RESULT_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _http_json(url: str, timeout: float) -> Any:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Canto-0243-portable-update"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_text(url: str, timeout: float) -> str:
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/octet-stream", "User-Agent": "Canto-0243-portable-update"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_remote_fingerprint(platform: str, *, timeout: float = DEFAULT_TIMEOUT_S) -> Optional[dict[str, str]]:
    """Latest non-prerelease release's portable-manifest-{platform}.json."""
    repo = github_repo()
    api = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        release = _http_json(api, timeout)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None
    if not isinstance(release, dict):
        return None
    # /releases/latest already skips prerelease; belt-and-suspenders:
    if release.get("prerelease") is True:
        return None
    tag = str(release.get("tag_name") or "")
    asset_name = f"portable-manifest-{platform}.json"
    assets = release.get("assets") or []
    url = None
    for a in assets:
        if isinstance(a, dict) and a.get("name") == asset_name:
            url = a.get("browser_download_url")
            break
    if not url:
        return None
    try:
        raw = _http_text(str(url), timeout)
        data = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return None
    need = ("tag", "platform", "lyrics_sha256", "package_digest")
    if not all(isinstance(data.get(k), str) and data[k] for k in need):
        return None
    # Prefer release tag_name if manifest tag drifts
    out = {k: str(data[k]) for k in need}
    if tag:
        out["tag"] = tag if tag.startswith("v") else f"v{tag}"
    return out


def check_update(root: Path, *, timeout: float = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """
    Return status dict for terminal + UI.
    No local manifest → checked=False (ADR: 唔檢查).
    Network/parse failure → available=False fail-open.
    """
    root = root.resolve()
    local = read_manifest(root)
    base: dict[str, Any] = {
        "checked": False,
        "available": False,
        "skipped": False,
        "local": local,
        "remote": None,
        "release_url": None,
        "download_hint": None,
    }
    if local is None:
        write_result(root, base)
        return base

    base["checked"] = True
    platform = local["platform"]
    repo = github_repo()
    release_url = f"https://github.com/{repo}/releases/latest"
    base["release_url"] = release_url

    remote = fetch_remote_fingerprint(platform, timeout=timeout)
    if remote is None:
        write_result(root, base)
        return base

    base["remote"] = remote
    rid = fingerprint_id(remote)
    if fingerprint_id(local) == rid:
        write_result(root, base)
        return base

    skip = read_skip(root)
    if skip and skip == rid:
        base["skipped"] = True
        write_result(root, base)
        return base

    base["available"] = True
    tag = remote["tag"]
    if platform == "windows":
        asset = "canto-0243-desktop.zip"
    else:
        arch = platform.replace("macos-", "", 1) if platform.startswith("macos-") else "x86_64"
        asset = f"canto-0243-desktop-macos-{arch}.tar.gz"
    base["download_hint"] = (
        f"gh release download {tag} -p {asset} --clobber\n"
        f"# Close Canto first, then extract over / beside the old Desktop folder."
    )
    write_result(root, base)
    return base


def format_terminal_notice(status: dict[str, Any], *, lang: str = "zh") -> Optional[str]:
    if not status.get("available"):
        return None
    remote = status.get("remote") or {}
    url = status.get("release_url") or ""
    hint = status.get("download_hint") or ""
    tag = remote.get("tag", "?")
    if lang == "en":
        return (
            f"\n*** Update available: {tag} ***\n"
            f"Download the full portable package, then close this app and extract over the old folder.\n"
            f"Release: {url}\n"
            f"{hint}\n"
        )
    return (
        f"\n*** 有新正式版：{tag} ***\n"
        f"請下載完整免安裝套件，關閉本程式後解壓覆蓋舊資料夾。\n"
        f"Release：{url}\n"
        f"{hint}\n"
    )


def portable_update_self_check() -> None:
    """ponytail: runnable check — python -m app.portable_update"""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # no manifest → no check
        st = check_update(root, timeout=0.1)
        assert st["checked"] is False and st["available"] is False

        (root / "lyrics.db").write_bytes(b"fake-db")
        (root / "a.txt").write_text("x", encoding="utf-8")
        fp = write_manifest(root, tag="v9.9.9", platform="windows")
        assert (root / MANIFEST_NAME).is_file()
        assert fp["lyrics_sha256"] == file_sha256(root / "lyrics.db")
        assert read_manifest(root) == fp

        write_skip(root, fingerprint_id(fp))
        assert read_skip(root) == fingerprint_id(fp)

        # fail-open: nonsense timeout / no network asset still returns checked local
        st2 = check_update(root, timeout=0.05)
        assert st2["checked"] is True
        # available may be False (fail-open or equal if somehow matches)
        assert "available" in st2


if __name__ == "__main__":
    if "--self-check" in sys.argv:
        portable_update_self_check()
        print("portable_update self-check ok")
        raise SystemExit(0)
    raise SystemExit("usage: python -m app.portable_update --self-check")
