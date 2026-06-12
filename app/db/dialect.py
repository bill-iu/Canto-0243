"""Cross-database SQL expression helpers."""

from __future__ import annotations

from sqlalchemy import func

from app.db.connection import IS_POSTGRES


def contains_substring(column, substr: str):
    """可移植的子字串檢查（PostgreSQL: strpos；SQLite: instr）。"""
    if IS_POSTGRES:
        return func.strpos(column, substr) > 0
    return func.instr(column, substr) > 0
