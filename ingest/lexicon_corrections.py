"""詞庫勘誤 — batch apply maintainer corrections to lyrics.db (CONTEXT § 詞庫勘誤).

Shared model + TSV load/save now live in app/lexicon/corrections.py so the
lexicon corrections UI + queue work in portable bundles (no 'ingest/' dir needed).
This module re-exports for back-compat with ingest CLI / scripts / tests.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from sqlalchemy.orm import Session

from app.lexicon.corrections import (
    ACTIONS,
    DEFAULT_TSV,
    FIELDS,
    LexiconCorrection,
    load_corrections,
    save_corrections,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BATCH_N = 20


def _find_word(db: Session, corr: LexiconCorrection):
    from app.models.word import Word

    matches = (
        db.query(Word)
        .filter(
            Word.char == corr.char,
            Word.code == corr.code,
            Word.jyutping == corr.jyutping,
        )
        .all()
    )
    if len(matches) != 1:
        raise ValueError(
            f"expected 1 word row for {corr.char!r} code={corr.code!r} jyutping={corr.jyutping!r}, "
            f"found {len(matches)}"
        )
    return matches[0]


def _set_jyutping(row, jyutping: str) -> None:
    from app.utils.jyutping_codec import get_0243_code, split_jyutping

    row.jyutping = jyutping
    row.code = get_0243_code(jyutping)
    initials, finals, _tones = split_jyutping(jyutping)
    row.initials = initials
    row.finals = finals
    if row.length is None or row.length == 0:
        row.length = len(row.char or "")


def apply_one(db: Session, corr: LexiconCorrection) -> str:
    if corr.action not in ACTIONS:
        raise ValueError(f"unknown action {corr.action!r}")
    if corr.action == "set_jyutping" and not corr.value:
        raise ValueError(f"set_jyutping requires value for {corr.char!r}")
    if corr.action == "set_code" and not corr.value:
        raise ValueError(f"set_code requires value for {corr.char!r}")

    row = _find_word(db, corr)
    if corr.action == "delete":
        db.delete(row)
        return "deleted"
    if corr.action == "set_code":
        word_len = len(row.char or "")
        if len(corr.value) != word_len:
            raise ValueError(
                f"set_code value {corr.value!r} length {len(corr.value)} "
                f"!= char length {word_len} for {corr.char!r}"
            )
        row.code = corr.value
        return f"set_code -> {corr.value}"
    _set_jyutping(row, corr.value)
    return f"set_jyutping -> {corr.value} (code {row.code})"


def check_status(
    rows: list[LexiconCorrection],
    *,
    batch_n: int = DEFAULT_BATCH_N,
    out: TextIO | None = None,
) -> int:
    sink = out or sys.stdout
    pending = [r for r in rows if r.is_pending]
    applied = len(rows) - len(pending)
    sink.write(f"lexicon corrections: {len(pending)} pending, {applied} applied\n")
    if pending:
        sink.write("pending:\n")
        for r in pending:
            sink.write(f"  {r.char}\t{r.code}\t{r.jyutping}\t{r.action}\t{r.value}\n")
    if len(pending) >= batch_n:
        sink.write(f"\n>= {batch_n} pending — consider: python -m ingest apply-lexicon-corrections --apply\n")
    return 0 if pending else 0


def apply_pending(
    db: Session,
    rows: list[LexiconCorrection],
    *,
    dry_run: bool = False,
    out: TextIO | None = None,
) -> tuple[list[LexiconCorrection], list[str]]:
    sink = out or sys.stdout
    logs: list[str] = []
    today = date.today().isoformat()
    updated = list(rows)
    pending_idxs = [i for i, r in enumerate(updated) if r.is_pending]
    if not pending_idxs:
        sink.write("No pending corrections.\n")
        return updated, logs

    for i in pending_idxs:
        corr = updated[i]
        if dry_run:
            logs.append(f"would apply: {corr.char} {corr.action} {corr.value}".strip())
            continue
        msg = apply_one(db, corr)
        logs.append(f"applied: {corr.char} code={corr.code} jyutping={corr.jyutping} -> {msg}")
        updated[i] = LexiconCorrection(
            char=corr.char,
            code=corr.code,
            jyutping=corr.jyutping,
            action=corr.action,
            value=corr.value,
            note=corr.note,
            status="applied",
            applied_at=today,
        )
    for line in logs:
        sink.write(line + "\n")
    return updated, logs


def post_apply_exports(repo_root: Path = REPO_ROOT) -> None:
    """B plan: export lexicon + README word count after db apply."""
    db = repo_root / "lyrics.db"
    lexicon = repo_root / "dist" / "words-lexicon.json"
    lexicon.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "export_words_lexicon.py"), "-o", str(lexicon)],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "update_readme_words_count.py"), "--db", str(db)],
        cwd=repo_root,
        check=True,
    )
