"""詞庫發佈閘 — v1.0.7 I2 (ADR CONTEXT § 詞庫發佈閘)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

# Baseline before v1.0.7 I2 phrase+index work (maintainer snapshot).
BASELINE_RIME_PHRASE_ROWS = 299_659
MAX_DB_BYTES = 95 * 1024 * 1024
MAX_INDEX_BYTES = 45 * 1024 * 1024
MIN_PHRASE_REJECT_RATIO = 0.50


@dataclass(frozen=True)
class ReleaseGateResult:
    ok: bool
    messages: tuple[str, ...]


def _index_bytes(conn: sqlite3.Connection) -> int | None:
    """Index payload via dbstat when available (not on all Windows sqlite builds)."""
    try:
        row = conn.execute(
            "SELECT SUM(pgsize) FROM dbstat WHERE name IN "
            "(SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%')"
        ).fetchone()
        return int(row[0] or 0)
    except sqlite3.OperationalError:
        return None


def check_lexicon_release_gate(
    db_path: Path | str,
    *,
    baseline_phrase_rows: int = BASELINE_RIME_PHRASE_ROWS,
) -> ReleaseGateResult:
    path = Path(db_path)
    msgs: list[str] = []
    ok = True
    if not path.is_file():
        return ReleaseGateResult(False, (f"missing db: {path}",))

    size = path.stat().st_size
    if size > MAX_DB_BYTES:
        ok = False
        msgs.append(f"db {size / 1024 / 1024:.1f} MB > {MAX_DB_BYTES / 1024 / 1024:.0f} MB cap")
    else:
        msgs.append(f"db {size / 1024 / 1024:.1f} MB OK")

    with sqlite3.connect(path) as conn:
        idx = _index_bytes(conn)
        if idx is None:
            msgs.append("indexes n/a (sqlite build has no dbstat; skipped)")
        elif idx > MAX_INDEX_BYTES:
            ok = False
            msgs.append(f"indexes {idx / 1024 / 1024:.1f} MB > {MAX_INDEX_BYTES / 1024 / 1024:.0f} MB cap")
        else:
            msgs.append(f"indexes {idx / 1024 / 1024:.1f} MB OK")

        phrase_rows = conn.execute(
            "SELECT COUNT(*) FROM words WHERE source_flags & 8 > 0"
        ).fetchone()[0]
        if baseline_phrase_rows > 0:
            kept_ratio = 1 - (phrase_rows / baseline_phrase_rows)
            if kept_ratio < MIN_PHRASE_REJECT_RATIO:
                ok = False
                msgs.append(
                    f"rime_phrase rows {phrase_rows} rejected only {kept_ratio * 100:.1f}% "
                    f"(need >={MIN_PHRASE_REJECT_RATIO * 100:.0f}%)"
                )
            else:
                msgs.append(f"rime_phrase reject {kept_ratio * 100:.1f}% OK ({phrase_rows} rows left)")

    return ReleaseGateResult(ok, tuple(msgs))


__all__ = ["ReleaseGateResult", "check_lexicon_release_gate", "BASELINE_RIME_PHRASE_ROWS"]