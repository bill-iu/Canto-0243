#!/usr/bin/env python3
"""Portable/PWA parity check for workbench line-reading choices."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.models.word import Word
from app.services.workbench.line_readings import resolve_line_readings
from tests.smoke.helpers import memory_sessionmaker


ROWS = [
    {"char": "香", "code": "3", "jyutping": "hoeng1"},
    {"char": "港", "code": "9", "jyutping": "gong2"},
    {"char": "你", "code": "5", "jyutping": "nei5"},
    {"char": "你", "code": "5", "jyutping": "lei5"},
    {"char": "難", "code": "0", "jyutping": "no4"},
    {"char": "難", "code": "0", "jyutping": "naan4"},
    {"char": "難", "code": "0", "jyutping": "naan4"},
]
SURFACE = "香港你難，𠮶"


def _portable() -> list[dict]:
    Session = memory_sessionmaker()
    with Session() as db:
        db.add_all([Word(**row, length=1) for row in ROWS])
        db.commit()
        slots = resolve_line_readings(SURFACE, db, allow_inject=False)
    return [
        {
            "surface": slot.surface,
            "kind": slot.kind,
            "choices": [
                {
                    "jyutping": choice.jyutping,
                    "code": choice.code,
                    "initial": choice.initial,
                    "final": choice.final,
                }
                for choice in slot.choices
            ],
            "needsChoice": slot.needs_choice,
        }
        for slot in slots
    ]


def _pwa() -> list[dict]:
    pron_rank = {
        f"{row['char']}\t{row['jyutping']}": pron_rank_sort_value_for_word(
            row["char"], row["jyutping"]
        )
        for row in ROWS
    }
    payload = json.dumps(
        {"surface": SURFACE, "rows": ROWS, "pronRank": pron_rank},
        ensure_ascii=False,
    ).encode("utf-8")
    proc = subprocess.run(
        [
            os.environ.get("NODE", "node"),
            "--experimental-strip-types",
            "scripts/workbench-line-readings-run.ts",
            base64.b64encode(payload).decode("ascii"),
        ],
        cwd=REPO_ROOT / "client",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"PWA runner failed\n{proc.stderr}")
    return json.loads(proc.stdout)


def main() -> int:
    portable = _portable()
    pwa = _pwa()
    if portable != pwa:
        print(json.dumps({"portable": portable, "pwa": pwa}, ensure_ascii=False, indent=2))
        return 1
    print("workbench line readings parity ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
