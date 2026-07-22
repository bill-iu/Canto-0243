"""Workbench span / line limits (ADR-0069). Mirror client/src/workbench/limits.ts."""

from __future__ import annotations

# One line / 替換段 hard max (= 工作台起句).
WORKBENCH_MAX_SLOTS = 64

# Observed max words.char length; skip candidate query when span wider.
# Independent of relation MAX_WORD_LEN (12). ponytail: open-db max(length).
WORKBENCH_LEXICON_MAX_WORD_LEN = 20

WORKBENCH_PHONEME_MIDDLE_MAX_WIDTH = 6

__all__ = [
    "WORKBENCH_LEXICON_MAX_WORD_LEN",
    "WORKBENCH_MAX_SLOTS",
    "WORKBENCH_PHONEME_MIDDLE_MAX_WIDTH",
]
