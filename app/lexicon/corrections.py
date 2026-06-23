"""Lexicon corrections TSV model and I/O (shared for app runtime + ingest tooling).

This lives under app/ so it is included in portable zero-install bundles (see build-portable).
Ingest tooling re-exports for CLI / apply back-compat.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

FIELDS = ("char", "code", "jyutping", "action", "value", "note", "status", "applied_at")
ACTIONS = frozenset({"set_jyutping", "set_code", "delete"})

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TSV = REPO_ROOT / "data" / "lexicon" / "lexicon_corrections.tsv"


@dataclass
class LexiconCorrection:
    char: str
    code: str
    jyutping: str
    action: str
    value: str
    note: str
    status: str
    applied_at: str

    @property
    def is_pending(self) -> bool:
        return self.status.strip().lower() == "pending"


def load_corrections(path: Path = DEFAULT_TSV) -> list[LexiconCorrection]:
    if not path.is_file():
        return []
    rows: list[LexiconCorrection] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for raw in reader:
            if not raw.get("char", "").strip():
                continue
            rows.append(
                LexiconCorrection(
                    char=raw["char"].strip(),
                    code=(raw.get("code") or "").strip(),
                    jyutping=(raw.get("jyutping") or "").strip(),
                    action=(raw.get("action") or "").strip(),
                    value=(raw.get("value") or "").strip(),
                    note=(raw.get("note") or "").strip(),
                    status=(raw.get("status") or "pending").strip(),
                    applied_at=(raw.get("applied_at") or "").strip(),
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
                    "code": row.code,
                    "jyutping": row.jyutping,
                    "action": row.action,
                    "value": row.value,
                    "note": row.note,
                    "status": row.status,
                    "applied_at": row.applied_at,
                }
            )
