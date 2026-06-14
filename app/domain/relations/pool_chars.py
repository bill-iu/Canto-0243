"""Backward-compatible re-export — prefer pool_projection."""

from __future__ import annotations

from app.domain.relations.pool_projection import relation_chars_for_seed

__all__ = ["relation_chars_for_seed"]
