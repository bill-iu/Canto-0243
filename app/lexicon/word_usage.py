"""Word familiarity is independent of pronunciation and lexicon admission."""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.lexicon.essay_index import get_essay_frequency
from app.payload_root import get_payload_root


@dataclass(frozen=True)
class WordUsage:
    rank: int
    subtitle_channels: int
    withdraw_curated: bool


def essay_usage_rank(frequency: int) -> int:
    """Conservative fallback; no corpus entry is not a withdrawal decision."""
    return 0 if frequency >= 1000 else 1 if frequency >= 500 else 2


def load_word_usage(path: Path | str | None = None) -> dict[str, WordUsage]:
    source = Path(path) if path is not None else get_payload_root() / "data/lexicon/word_usage.tsv"
    return _load_word_usage(source)


@lru_cache(maxsize=4)
def _load_word_usage(source: Path) -> dict[str, WordUsage]:
    if not source.is_file():
        return {}  # Legacy payloads and isolated fixtures retain their Essay order.
    result: dict[str, WordUsage] = {}
    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"char", "usage_rank", "subtitle_channels", "action"}
        if not required.issubset(reader.fieldnames or []) or len(set(reader.fieldnames or [])) != len(reader.fieldnames or []):
            raise ValueError(f"Invalid word usage header: {source}")
        for line, row in enumerate(reader, 2):
            char = (row.get("char") or "").strip()
            try:
                if not re.fullmatch(r"[0-3]", row.get("usage_rank") or "") or not re.fullmatch(r"[0-9]+", row.get("subtitle_channels") or ""):
                    raise ValueError("Non-decimal usage grade")
                rank = int(row["usage_rank"])
                channels = int(row["subtitle_channels"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid word usage numbers: {source}:{line}") from exc
            action = row["action"]
            if not char or rank not in range(4) or not 0 <= channels <= 9007199254740991 or action not in {"keep", "withdraw_curated"}:
                raise ValueError(f"Invalid word usage row: {source}:{line}")
            if (rank == 3) != (action == "withdraw_curated"):
                raise ValueError(f"Conflicting word usage action: {source}:{line}")
            value = WordUsage(rank, channels, action == "withdraw_curated")
            if char in result and result[char] != value:
                raise ValueError(f"Conflicting word usage grade: {char}")
            result[char] = value
    return result


def reset_word_usage_for_tests() -> None:
    _load_word_usage.cache_clear()


def word_usage_sort_key(char: str) -> tuple[int, int]:
    literal = (char or "").strip()
    value = load_word_usage().get(literal)
    if value is not None:
        return value.rank, -value.subtitle_channels
    return essay_usage_rank(get_essay_frequency(literal)), 0
