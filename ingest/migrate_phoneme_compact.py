"""
One-shot: convert words.initials/finals from JSON arrays to S1 compact (ADR-0037 M1).
Also writes lexicon_meta phoneme vocab fingerprint.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from app.domain.lexicon.phoneme_codec import encode_phoneme_list, is_compact_phoneme_field
from ingest.lexicon_meta import write_phoneme_vocab_meta


def _json_list(raw: object) -> list[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x) if x is not None else "" for x in raw]
    if not isinstance(raw, str):
        return []
    s = raw.strip()
    if not s:
        return []
    if s[0] != "[":
        return []
    try:
        parsed = json.loads(s)
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(x) if x is not None else "" for x in parsed]


def migrate_db(db_path: Path | str, *, vacuum: bool = True) -> tuple[int, int]:
    """Returns (rows_updated, rows_skipped_already_compact)."""
    path = Path(db_path)
    updated = 0
    skipped = 0
    with sqlite3.connect(path) as conn:
        rows = conn.execute("SELECT rowid, initials, finals FROM words").fetchall()
        for rowid, ini_raw, fin_raw in rows:
            if is_compact_phoneme_field(ini_raw) and is_compact_phoneme_field(fin_raw):
                # compact or empty — still re-encode empty lists consistently
                if (ini_raw or "") == "" and (fin_raw or "") == "":
                    skipped += 1
                    continue
                if isinstance(ini_raw, str) and ini_raw and ini_raw[0] != "[":
                    if isinstance(fin_raw, str) and (not fin_raw or fin_raw[0] != "["):
                        skipped += 1
                        continue
            ini_parts = _json_list(ini_raw)
            fin_parts = _json_list(fin_raw)
            if not ini_parts and not fin_parts and (ini_raw or fin_raw):
                # unreadable non-empty — leave
                skipped += 1
                continue
            new_ini = encode_phoneme_list(ini_parts, "initial") if ini_parts else ""
            new_fin = encode_phoneme_list(fin_parts, "final") if fin_parts else ""
            conn.execute(
                "UPDATE words SET initials = ?, finals = ? WHERE rowid = ?",
                (new_ini, new_fin, rowid),
            )
            updated += 1
        conn.commit()
        if vacuum:
            conn.execute("VACUUM")
    write_phoneme_vocab_meta(path)
    return updated, skipped


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m ingest.migrate_phoneme_compact <lyrics.db> [--no-vacuum]")
        return 2
    path = Path(args[0])
    vacuum = "--no-vacuum" not in args
    if not path.is_file():
        print(f"missing {path}")
        return 1
    u, s = migrate_db(path, vacuum=vacuum)
    print(f"OK compact migrate {path}: updated={u} skipped={s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
