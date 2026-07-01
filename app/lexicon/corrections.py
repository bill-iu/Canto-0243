"""Lexicon corrections TSV model and I/O (shared for app runtime + ingest tooling).

This lives under app/ so it is included in portable zero-install bundles (see build-portable).
Ingest tooling re-exports for CLI / apply back-compat.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

FIELDS = ("char", "old_jyutping", "old_code", "action", "value", "note")
LEGACY_FIELDS = ("char", "code", "jyutping", "action", "value", "note", "status", "applied_at")
ACTIONS = frozenset({"set_jyutping", "set_code", "delete"})

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = REPO_ROOT / "data" / "lexicon" / "lexicon_corrections.tsv"


@dataclass
class LexiconCorrection:
    char: str
    old_jyutping: str
    old_code: str = ""
    action: str = ""
    value: str = ""
    note: str = ""

    # ponytail: back-compat for callers still passing legacy positional args
    @property
    def code(self) -> str:
        return self.old_code

    @property
    def jyutping(self) -> str:
        return self.old_jyutping


def load_corrections(path: Path = DEFAULT_TSV) -> list[LexiconCorrection]:
    if not path.is_file():
        return []
    rows: list[LexiconCorrection] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for raw in reader:
            if not raw.get("char", "").strip():
                continue
            old_jyutping = (raw.get("old_jyutping") or raw.get("jyutping") or "").strip()
            old_code = (raw.get("old_code") or raw.get("code") or "").strip()
            rows.append(
                LexiconCorrection(
                    char=raw["char"].strip(),
                    old_jyutping=old_jyutping,
                    old_code=old_code,
                    action=(raw.get("action") or "").strip(),
                    value=(raw.get("value") or "").strip(),
                    note=(raw.get("note") or "").strip(),
                )
            )
    return rows


def save_corrections(rows: list[LexiconCorrection], path: Path = DEFAULT_TSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "char": row.char,
                    "old_jyutping": row.old_jyutping,
                    "old_code": row.old_code,
                    "action": row.action,
                    "value": row.value,
                    "note": row.note,
                }
            )
