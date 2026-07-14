"""專案自建反義唔可同 build-db 同輪靜態近義衝突（cilin 葉組全量，唔係度上限後 DB）。"""

from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from ingest.project_antonyms import normalize_literal, pair_undirected_key
from ingest.word_relations_build import same_round_static_parts

ROOT = Path(__file__).resolve().parents[2]
TSV = ROOT / "data" / "syn_ant" / "project_antonyms.tsv"


class ProjectAntStaticSynGateTests(unittest.TestCase):
    def test_no_project_ant_static_syn_conflict(self) -> None:
        rows: list[tuple[str, str]] = []
        for line in TSV.read_text(encoding="utf-8").splitlines()[1:]:
            if not line.strip():
                continue
            head, tail, *_ = line.split("\t")
            rows.append((normalize_literal(head), normalize_literal(tail)))

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        seen: set[str] = set()
        for head, tail in rows:
            for ch in (head, tail):
                if ch in seen:
                    continue
                seen.add(ch)
                db.add(
                    Word(
                        char=ch,
                        jyutping="aa1",
                        code="0",
                        initials="[]",
                        finals="[]",
                        length=len(ch),
                    )
                )
        db.commit()
        try:
            _flat, static_syn = same_round_static_parts(db)
        finally:
            db.close()

        conflicts = [
            (h, t) for h, t in rows if pair_undirected_key(h, t) in static_syn
        ]
        self.assertEqual(
            conflicts,
            [],
            f"project_ant syn conflicts (build-db would fail): {conflicts}",
        )


if __name__ == "__main__":
    unittest.main()
