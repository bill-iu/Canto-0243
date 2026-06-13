"""Runtime loader for curated 近義複合詞 list."""

from __future__ import annotations

from pathlib import Path
from typing import List, Set

DEFAULT_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "syn_ant" / "compound_synonyms.txt"
)


def load_compound_synonyms(path: Path | None = None) -> List[str]:
    """Load deduplicated 2-char compound list (order preserved)."""
    p = path or DEFAULT_PATH
    if not p.exists():
        return []
    seen: Set[str] = set()
    out: List[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for token in line.replace("，", " ").replace(",", " ").split():
            ch = token.strip()
            if len(ch) != 2 or ch in seen:
                continue
            seen.add(ch)
            out.append(ch)
    return out
