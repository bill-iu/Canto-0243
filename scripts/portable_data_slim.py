"""C11-B: denylist slim of portable data/ (runtime-only; cut extract/delete file count)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Iterable

# Directory basenames removed wherever they appear under data/.
_DIR_BASENAME_DENY = frozenset(
    {
        "audit",
        "fixtures",
        "raw",  # ingest sources; not queried at runtime
        "proposals",
        "locks",
    }
)

# POS SSOT + mother bodies live in git; runtime reads project-pos-index.json (ADR-0058).
_TOP_DIR_DENY = frozenset({"pos"})

# Must survive slim — offline preload / thesaurus / compound lists.
REQUIRED_RUNTIME_RELPATHS = (
    "cilin/new_cilin.txt",
    "thesaurus/dict_synonym.txt",
    "thesaurus/dict_antonym.txt",
    "syn_ant/compound_synonyms.txt",
    "syn_ant/compound_antonyms.txt",
    "rime/char.csv",
    "essay/essay-cantonese.txt",
    "lexicon/curated_common.txt",
    "lexicon/lexicon_corrections.tsv",
)


def count_files(root: Path) -> int:
    if not root.is_dir():
        return 0
    return sum(1 for p in root.rglob("*") if p.is_file())


def data_copy_ignore(_directory: str, names: Iterable[str]) -> list[str]:
    """shutil.copytree ignore for data/ materialize."""
    skip = set(_DIR_BASENAME_DENY) | set(_TOP_DIR_DENY) | {"__pycache__", "project"}
    return [n for n in names if n in skip]


def robocopy_exclude_dirs() -> list[str]:
    """Directory names for robocopy /XD when copying data/."""
    return sorted(_DIR_BASENAME_DENY | _TOP_DIR_DENY | {"__pycache__", "project"})


def _should_remove_dir(path: Path, data_root: Path) -> bool:
    if path.name in _DIR_BASENAME_DENY:
        return True
    try:
        rel = path.relative_to(data_root)
    except ValueError:
        return False
    if len(rel.parts) == 1 and rel.parts[0] in _TOP_DIR_DENY:
        return True
    # Maintainer campaign tree beside compound_*.txt
    if rel.as_posix() == "syn_ant/project":
        return True
    return False


def _should_remove_file(path: Path, data_root: Path) -> bool:
    """Campaign / maintainer leftovers that sit beside runtime files."""
    try:
        rel = path.relative_to(data_root)
    except ValueError:
        return False
    name = path.name
    if name.startswith("campaign"):
        return True
    if rel.as_posix() in REQUIRED_RUNTIME_RELPATHS:
        return False
    if len(rel.parts) == 2 and rel.parts[0] == "syn_ant":
        if name.startswith(("project", "ant_")):
            return True
        if "prompt" in name:
            return True
        if name in {"sources.yaml"} or name.endswith(".meta.json"):
            return True
    if len(rel.parts) == 2 and rel.parts[0] == "lexicon":
        # Build manifests / full lexicon JSON — already baked into lyrics.db.
        if name in {
            "sources.yaml",
            "cantonese_md_lexicon.json",
            "cantonese_md.manifest.json",
            "unihan_cantonese.json",
            "unihan_cantonese.manifest.json",
            "curated_lexicon.json",
        }:
            return True
    if len(rel.parts) == 2 and rel.parts[0] == "antonym":
        # antisem.txt is ingest source; ant edges live in lyrics.db.
        if name.endswith((".txt", ".tsv")):
            return True
    return False


def _iter_removable_dirs(data_root: Path) -> list[Path]:
    found = [p for p in data_root.rglob("*") if p.is_dir() and _should_remove_dir(p, data_root)]
    found.sort(key=lambda p: len(p.parts), reverse=True)
    return found


def assert_runtime_data(data_dir: Path) -> None:
    missing = [rel for rel in REQUIRED_RUNTIME_RELPATHS if not (data_dir / rel).is_file()]
    if missing:
        raise FileNotFoundError(f"portable data missing runtime files: {missing}")


def slim_portable_data(data_dir: Path) -> dict[str, int]:
    """Remove denylisted trees/files; return before/after counts."""
    data_dir = data_dir.resolve()
    if not data_dir.is_dir():
        raise FileNotFoundError(data_dir)

    before = count_files(data_dir)
    removed_dirs = 0
    for path in _iter_removable_dirs(data_dir):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
            removed_dirs += 1

    removed_files = 0
    for path in list(data_dir.rglob("*")):
        if path.is_file() and _should_remove_file(path, data_dir):
            try:
                path.unlink()
                removed_files += 1
            except OSError:
                pass

    assert_runtime_data(data_dir)

    stats = {
        "data_files_before": before,
        "dirs_removed": removed_dirs,
        "files_removed": removed_files,
    }
    report = data_dir / "portable-data-slim.json"
    report.write_text("{}\n", encoding="utf-8")
    after = count_files(data_dir)
    stats["data_files_after"] = after
    stats["data_files_removed"] = max(0, before - after)
    report.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return stats


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Slim portable data/ (C11-B)")
    p.add_argument("data_dir", type=Path, help="Path to staged portable data/")
    args = p.parse_args()
    stats = slim_portable_data(args.data_dir)
    print(
        "Portable data slim (C11-B): "
        f"{stats['data_files_before']} -> {stats['data_files_after']} files "
        f"(-{stats['data_files_removed']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
