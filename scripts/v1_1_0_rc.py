#!/usr/bin/env python3
"""Integrity contract for the one-off v1.1.0 local release candidate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


TAG = "v1.1.0"
SCHEMA_VERSION = 1
BASE_ARTIFACT_PATHS = (
    "lyrics.db",
    "dist/words-lexicon.json",
    "dist/canto-0243-portable.zip",
    "dist/portable-manifest-windows.json",
    "dist/canto-0243-pages-v1.1.0.tar.gz",
)
CHECKSUM_PATH = "dist/v1.1.0-SHA256SUMS.txt"
ARTIFACT_PATHS = BASE_ARTIFACT_PATHS + (CHECKSUM_PATH,)
CHECK_NAMES = (
    "build-db",
    "project-pos",
    "rc-contract",
    "pos-self-checks",
    "portable-host-build",
    "pwa-build",
    "pages-package",
    "windows-portable",
    "relocated-portable-smoke",
)
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


class ContractError(ValueError):
    pass


def require_identity(tag: str, source_commit: str) -> None:
    if tag != TAG:
        raise ContractError(f"v1.1.0 only: received {tag!r}")
    if not COMMIT_RE.fullmatch(source_commit):
        raise ContractError("source commit must be a full 40-character lowercase SHA-1")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stream_sha256(stream: object) -> str:
    digest = hashlib.sha256()
    while True:
        chunk = stream.read(1024 * 1024)  # type: ignore[attr-defined]
        if not chunk:
            return digest.hexdigest()
        digest.update(chunk)


def artifact_record(root: Path, relative: str) -> dict[str, object]:
    path = root / relative
    if not path.is_file():
        raise ContractError(f"missing RC artifact: {relative}")
    return {"path": relative, "size": path.stat().st_size, "sha256": sha256(path)}


def validate_candidate_relationships(root: Path) -> None:
    sidecar_path = root / "dist" / "portable-manifest-windows.json"
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid portable sidecar: {exc}") from exc
    if not isinstance(sidecar, dict):
        raise ContractError("invalid portable sidecar: root must be an object")
    if sidecar.get("tag") != TAG or sidecar.get("platform") != "windows":
        raise ContractError("portable sidecar must identify v1.1.0/windows")
    if sidecar.get("lyrics_sha256") != sha256(root / "lyrics.db"):
        raise ContractError("portable lyrics_sha256 does not match candidate lyrics.db")
    if not re.fullmatch(r"[0-9a-f]{64}", str(sidecar.get("package_digest", ""))):
        raise ContractError("portable package_digest must be a lowercase SHA-256")
    zip_path = root / "dist" / "canto-0243-portable.zip"
    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = archive.namelist()
            if "lyrics.db" not in names or "portable-manifest.json" not in names:
                raise ContractError("portable zip is missing lyrics.db or portable-manifest.json")
            with archive.open("lyrics.db") as stream:
                if stream_sha256(stream) != sha256(root / "lyrics.db"):
                    raise ContractError("portable zip lyrics.db does not match candidate lyrics.db")
            embedded = json.loads(archive.read("portable-manifest.json").decode("utf-8"))
    except (OSError, zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid portable zip: {exc}") from exc
    if embedded != sidecar:
        raise ContractError("portable zip manifest does not match release sidecar")
    expected_checksums = "".join(
        f"{sha256(root / relative)}  {relative}\n" for relative in BASE_ARTIFACT_PATHS
    )
    try:
        actual_checksums = (root / CHECKSUM_PATH).read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"missing checksum file: {exc}") from exc
    if actual_checksums != expected_checksums:
        raise ContractError("v1.1.0 checksum file does not match candidate artifacts")


def write_checksums(root: Path, output: Path) -> None:
    for relative in BASE_ARTIFACT_PATHS:
        artifact_record(root, relative)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(f"{sha256(root / relative)}  {relative}\n" for relative in BASE_ARTIFACT_PATHS),
        encoding="utf-8",
    )


def create_manifest(
    root: Path,
    output: Path,
    tag: str,
    source_commit: str,
    passed_checks: list[str],
) -> None:
    require_identity(tag, source_commit)
    if tuple(passed_checks) != CHECK_NAMES:
        raise ContractError("all fixed v1.1.0 checks must pass in the required order")
    validate_candidate_relationships(root)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "tag": TAG,
        "source_commit": source_commit,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checks": [{"name": name, "status": "pass"} for name in CHECK_NAMES],
        "artifacts": [artifact_record(root, relative) for relative in ARTIFACT_PATHS],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid RC manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("invalid RC manifest: root must be an object")
    return value


def validate_pages(root: Path, source_dir: Path) -> None:
    for required in ("index.html", "workbench/index.html", "lexicon-manifest.json"):
        if not (source_dir / required).is_file():
            raise ContractError(f"Pages artifact missing {required}")
    db_files = sorted(path for path in source_dir.glob("lyrics*.db") if path.is_file())
    if len(db_files) != 1:
        raise ContractError(f"Pages artifact requires exactly one lyrics*.db, found {len(db_files)}")
    manifest = load_manifest(source_dir / "lexicon-manifest.json")
    page_db = db_files[0]
    if manifest.get("lexiconVersion") != TAG:
        raise ContractError("Pages lexiconVersion must be v1.1.0")
    if manifest.get("dbFile") != page_db.name:
        raise ContractError("Pages lexicon manifest dbFile mismatch")
    if manifest.get("byteSize") != page_db.stat().st_size:
        raise ContractError("Pages lexicon manifest byteSize mismatch")
    page_sha = sha256(page_db)
    if manifest.get("sha256") != page_sha:
        raise ContractError("Pages lexicon manifest sha256 mismatch")
    if page_sha != sha256(root / "lyrics.db"):
        raise ContractError("Pages lyrics.db does not match candidate lyrics.db")
    if any(path.is_symlink() for path in source_dir.rglob("*")):
        raise ContractError("Pages artifact must not contain symbolic links")


def pack_pages(root: Path, source_dir: Path, output: Path, tag: str) -> None:
    require_identity(tag, "0" * 40)
    validate_pages(root, source_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        for path in sorted(item for item in source_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(source_dir).as_posix()
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with path.open("rb") as stream:
                archive.addfile(info, stream)


def verify_file(manifest_path: Path, artifact_path: str, file_path: Path, source_commit: str) -> None:
    require_identity(TAG, source_commit)
    manifest = load_manifest(manifest_path)
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("tag") != TAG:
        raise ContractError("file verification requires a v1.1.0 RC manifest")
    if manifest.get("source_commit") != source_commit:
        raise ContractError("manifest source commit mismatch")
    if manifest.get("checks") != [{"name": name, "status": "pass"} for name in CHECK_NAMES]:
        raise ContractError("manifest check set mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ContractError("manifest artifacts must be a list")
    paths = tuple(item.get("path") for item in artifacts if isinstance(item, dict))
    if paths != ARTIFACT_PATHS or len(artifacts) != len(ARTIFACT_PATHS):
        raise ContractError("manifest artifact set is not the fixed v1.1.0 set")
    matches = [item for item in artifacts if isinstance(item, dict) and item.get("path") == artifact_path]
    if len(matches) != 1 or artifact_path not in ARTIFACT_PATHS:
        raise ContractError(f"artifact is not in the fixed v1.1.0 set: {artifact_path}")
    if not file_path.is_file():
        raise ContractError(f"missing downloaded artifact: {file_path}")
    actual = {"path": artifact_path, "size": file_path.stat().st_size, "sha256": sha256(file_path)}
    if matches[0] != actual:
        raise ContractError(f"artifact integrity mismatch: {artifact_path}")


def verify_manifest(root: Path, manifest_path: Path, tag: str, source_commit: str) -> None:
    require_identity(tag, source_commit)
    validate_candidate_relationships(root)
    manifest = load_manifest(manifest_path)
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("unsupported RC manifest schema")
    if manifest.get("tag") != TAG:
        raise ContractError("manifest tag is not v1.1.0")
    if manifest.get("source_commit") != source_commit:
        raise ContractError("manifest source commit mismatch")
    checks = manifest.get("checks")
    expected_checks = [{"name": name, "status": "pass"} for name in CHECK_NAMES]
    if checks != expected_checks:
        raise ContractError("manifest does not record every fixed v1.1.0 check as passed")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ContractError("manifest artifacts must be a list")
    paths = tuple(item.get("path") for item in artifacts if isinstance(item, dict))
    if paths != ARTIFACT_PATHS or len(artifacts) != len(ARTIFACT_PATHS):
        raise ContractError("manifest artifact set is not the fixed v1.1.0 set")
    for item, relative in zip(artifacts, ARTIFACT_PATHS, strict=True):
        expected = artifact_record(root, relative)
        if item != expected:
            raise ContractError(f"artifact integrity mismatch: {relative}")


def verify_remote_assets(
    root: Path,
    remote_dir: Path,
    manifest_path: Path,
    source_commit: str,
) -> list[str]:
    verify_manifest(root, manifest_path, TAG, source_commit)
    local_paths = [root / relative for relative in ARTIFACT_PATHS] + [manifest_path]
    expected = {path.name: path for path in local_paths}
    remote = {path.name: path for path in remote_dir.iterdir() if path.is_file()}
    extra = sorted(set(remote) - set(expected))
    if extra:
        raise ContractError(f"unexpected remote asset(s): {', '.join(extra)}")
    for name in sorted(set(remote) & set(expected)):
        if remote[name].stat().st_size != expected[name].stat().st_size or sha256(remote[name]) != sha256(expected[name]):
            raise ContractError(f"remote asset differs from accepted candidate: {name}")
    return [path.name for path in local_paths if path.name not in remote]


def fetch_bytes(base_url: str, relative: str) -> bytes:
    request = Request(
        urljoin(base_url.rstrip("/") + "/", relative),
        headers={"Cache-Control": "no-cache", "User-Agent": "Canto-0243-v1.1.0-RC"},
    )
    try:
        with urlopen(request, timeout=60) as response:
            if getattr(response, "status", 200) != 200:
                raise ContractError(f"live Pages returned HTTP {response.status}: {relative}")
            return response.read()
    except OSError as exc:
        raise ContractError(f"live Pages fetch failed for {relative}: {exc}") from exc


def live_smoke(root: Path, base_url: str) -> dict[str, object]:
    try:
        lexicon = json.loads(fetch_bytes(base_url, "lexicon-manifest.json"))
        carrier = json.loads(fetch_bytes(base_url, "project-pos-index.json"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"live Pages JSON is invalid: {exc}") from exc
    if not isinstance(lexicon, dict) or lexicon.get("lexiconVersion") != TAG:
        raise ContractError("live Pages lexiconVersion is not v1.1.0")
    db_name = lexicon.get("dbFile")
    if not isinstance(db_name, str) or Path(db_name).name != db_name:
        raise ContractError("live Pages dbFile is invalid")
    live_db = fetch_bytes(base_url, db_name)
    local_db = root / "lyrics.db"
    if lexicon.get("byteSize") != len(live_db) or lexicon.get("sha256") != hashlib.sha256(live_db).hexdigest():
        raise ContractError("live Pages database does not match its lexicon manifest")
    if len(live_db) != local_db.stat().st_size or hashlib.sha256(live_db).hexdigest() != sha256(local_db):
        raise ContractError("live Pages database does not match the accepted v1.1.0 candidate")
    connection = sqlite3.connect(f"file:{local_db.as_posix()}?mode=ro", uri=True)
    try:
        search_hit = connection.execute(
            "SELECT 1 FROM words WHERE char = ? LIMIT 1", ("鼻青眼腫",)
        ).fetchone()
    finally:
        connection.close()
    if search_hit is None:
        raise ContractError("accepted/live-identical database search missed 鼻青眼腫")
    literals = carrier.get("literals") if isinstance(carrier, dict) else None
    entry = literals.get("鼻青眼腫") if isinstance(literals, dict) else None
    expected = {
        "pos": ["a"],
        "trust": "high",
        "gate": ["a"],
        "show": ["a"],
        "family": "chengyu",
        "voice": "passive",
    }
    if entry != expected:
        raise ContractError(f"live Pages POS smoke mismatch for 鼻青眼腫: {entry!r}")
    if b"<html" not in fetch_bytes(base_url, "index.html").lower():
        raise ContractError("live Pages index.html smoke failed")
    return {"tag": TAG, "db_sha256": sha256(local_db), "search": "鼻青眼腫", "pos": entry}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("create-manifest", "verify-manifest"):
        command = commands.add_parser(name)
        command.add_argument("--tag", required=True)
        command.add_argument("--root", type=Path, required=True)
        command.add_argument("--source-commit", required=True)
        if name == "create-manifest":
            command.add_argument("--passed-check", action="append", default=[])
            command.add_argument("--output", type=Path, required=True)
        else:
            command.add_argument("--manifest", type=Path, required=True)
    pack = commands.add_parser("pack-pages")
    pack.add_argument("--tag", required=True)
    pack.add_argument("--root", type=Path, required=True)
    pack.add_argument("--source-dir", type=Path, required=True)
    pack.add_argument("--output", type=Path, required=True)
    verify_one = commands.add_parser("verify-file")
    verify_one.add_argument("--manifest", type=Path, required=True)
    verify_one.add_argument("--artifact-path", required=True)
    verify_one.add_argument("--source-commit", required=True)
    verify_one.add_argument("--file", type=Path, required=True)
    verify_pages_cmd = commands.add_parser("verify-pages")
    verify_pages_cmd.add_argument("--tag", required=True)
    verify_pages_cmd.add_argument("--root", type=Path, required=True)
    verify_pages_cmd.add_argument("--source-dir", type=Path, required=True)
    checksums = commands.add_parser("write-checksums")
    checksums.add_argument("--root", type=Path, required=True)
    checksums.add_argument("--output", type=Path, required=True)
    remote = commands.add_parser("verify-remote-assets")
    remote.add_argument("--root", type=Path, required=True)
    remote.add_argument("--remote-dir", type=Path, required=True)
    remote.add_argument("--manifest", type=Path, required=True)
    remote.add_argument("--source-commit", required=True)
    live = commands.add_parser("live-smoke")
    live.add_argument("--root", type=Path, required=True)
    live.add_argument("--base-url", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "create-manifest":
            create_manifest(
                args.root.resolve(),
                args.output.resolve(),
                args.tag,
                args.source_commit,
                args.passed_check,
            )
            print(f"created {args.output}")
        elif args.command == "verify-manifest":
            verify_manifest(args.root.resolve(), args.manifest.resolve(), args.tag, args.source_commit)
            print("v1.1.0 RC manifest verified")
        elif args.command == "pack-pages":
            pack_pages(args.root.resolve(), args.source_dir.resolve(), args.output.resolve(), args.tag)
            print(f"packed {args.output}")
        elif args.command == "verify-file":
            verify_file(
                args.manifest.resolve(),
                args.artifact_path,
                args.file.resolve(),
                args.source_commit,
            )
            print(f"verified {args.artifact_path}")
        elif args.command == "verify-pages":
            require_identity(args.tag, "0" * 40)
            validate_pages(args.root.resolve(), args.source_dir.resolve())
            print("v1.1.0 Pages files verified")
        elif args.command == "write-checksums":
            write_checksums(args.root.resolve(), args.output.resolve())
            print(f"wrote {args.output}")
        elif args.command == "verify-remote-assets":
            missing = verify_remote_assets(
                args.root.resolve(),
                args.remote_dir.resolve(),
                args.manifest.resolve(),
                args.source_commit,
            )
            print(json.dumps({"missing": missing}, separators=(",", ":")))
        else:
            print(json.dumps(live_smoke(args.root.resolve(), args.base_url), ensure_ascii=False))
    except ContractError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
