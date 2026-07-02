"""黃金查詢語意解釋集 — PWA explain parity."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_EXPLAINS_JSON = REPO_ROOT / "tests" / "smoke" / "golden_explains.json"


@dataclass(frozen=True)
class ExplainCase:
    query: str
    summary: str | None = None
    warning: str | None = None
    kind: str | None = None


def load_golden_explains() -> tuple[ExplainCase, ...]:
    raw = json.loads(GOLDEN_EXPLAINS_JSON.read_text(encoding="utf-8"))
    return tuple(
        ExplainCase(
            query=row["query"],
            summary=row.get("summary"),
            warning=row.get("warning"),
            kind=row.get("kind"),
        )
        for row in raw
    )


GOLDEN_EXPLAIN_CASES: tuple[ExplainCase, ...] = load_golden_explains()
