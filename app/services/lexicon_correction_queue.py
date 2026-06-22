"""Append pending rows to 詞庫勘誤 TSV."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ingest.lexicon_corrections import LexiconCorrection, load_corrections, save_corrections


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
    return (row.char, row.code, row.jyutping, row.action, row.value)


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
    if action not in {"set_jyutping", "set_code"}:
        raise LexiconCorrectionQueueError("invalid_action", "不支援的勘誤命令")
    if not value.strip():
        raise LexiconCorrectionQueueError("missing_value", "請提供修正值")

    new_row = LexiconCorrection(
        char=literal,
        code=code.strip(),
        jyutping=jyutping.strip(),
        action=action,
        value=value.strip(),
        note=note.strip(),
        status="pending",
        applied_at="",
    )
    rows = load_corrections(path)
    if any(r.is_pending and _row_key(r) == _row_key(new_row) for r in rows):
        raise LexiconCorrectionQueueError("duplicate", "此勘誤已有相同 pending 列")

    rows.append(new_row)
    save_corrections(rows, path)
    pending_count = sum(1 for r in rows if r.is_pending)
    return QueuedLexiconCorrection(
        message=f"已記錄勘誤（目前 {pending_count} 筆待套用）",
        pending_count=pending_count,
        row=new_row,
    )
