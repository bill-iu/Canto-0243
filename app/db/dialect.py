"""SQLite SQL expression helpers."""

from __future__ import annotations

from sqlalchemy import func


def contains_substring(column, substr: str):
    """子字串檢查（SQLite: instr）。"""
    return func.instr(column, substr) > 0
