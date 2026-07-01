"""Append rows to 詞庫勘誤 TSV (applied on build-db)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.lexicon.corrections import LexiconCorrection, load_corrections, save_corrections


@dataclass(frozen=True)
class QueuedLexiconCorrection:
    message: str
    pending_count: int
    row: LexiconCorrection


class LexiconCorrectionQueueError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _row_key(row: LexiconCorrection) -> tuple[str, str, str, str, str]:
    return (row.char, row.old_code, row.old_jyutping, row.action, row.value)


def queue_lexicon_correction(
    *,
    char: str,
    code: str,
    jyutping: str,
    action: str,
    value: str,
    note: str,
    path: Path,
) -> QueuedLexiconCorrection:
    literal = char.strip()
    if not literal:
        raise LexiconCorrectionQueueError("missing_char", "請提供字面")
    if action not in {"set_jyutping", "set_code", "delete"}:
        raise LexiconCorrectionQueueError("invalid_action", "不支援的勘誤命令")
    if action != "delete" and not value.strip():
        raise LexiconCorrectionQueueError("missing_value", "請提供修正值")

    new_row = LexiconCorrection(
        char=literal,
        old_jyutping=jyutping.strip(),
        old_code=code.strip(),
        action=action,
        value=value.strip(),
        note=note.strip(),
    )
    rows = load_corrections(path)
    if any(_row_key(r) == _row_key(new_row) for r in rows):
        raise LexiconCorrectionQueueError("duplicate", "此勘誤已有相同列")

    rows.append(new_row)
    save_corrections(rows, path)
    return QueuedLexiconCorrection(
        message=f"已記錄勘誤（共 {len(rows)} 筆；詞條庫建置命令時套用）",
        pending_count=len(rows),
        row=new_row,
    )
