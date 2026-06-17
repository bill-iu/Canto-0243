"""Dual phoneme anchor execution lives in 缺字型查詢執行 (ADR architecture #C)."""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_parse import build_jyutping_dual_match_specs, parse_query


class DualPhonemeEngineTests(unittest.TestCase):
    def test_execute_dual_phoneme_merges_and_tags_dimensions(self):
        from app.services.position_match.engine import execute_dual_phoneme_anchor_specs

        parsed = parse_query("3m4")
        self.assertTrue(getattr(parsed, "dual_phoneme", False))
        initial_spec, final_spec = build_jyutping_dual_match_specs(parsed)

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all(
            [
                Word(
                    id=1,
                    char="門人",
                    code="34",
                    jyutping="mun4 jan4",
                    finals='["un","an"]',
                    initials='["m","j"]',
                    length=2,
                ),
                Word(
                    id=2,
                    char="唔人",
                    code="34",
                    jyutping="m4 jan4",
                    finals='[""]',
                    initials='["m"]',
                    length=2,
                ),
            ]
        )
        session.commit()
        try:
            result = execute_dual_phoneme_anchor_specs(
                initial_spec,
                final_spec,
                code=None,
                mode="m1",
                limit=20,
                offset=0,
                db=session,
            )
        finally:
            session.close()

        by_dim: dict[str, list[str]] = {}
        for row in result.items:
            by_dim.setdefault(row.get("anchor_dimension"), []).append(row["char"])
        self.assertIn("門人", by_dim.get("initial", []))
        self.assertIn("唔人", by_dim.get("final", []))


class DualPhonemeSeamTests(unittest.TestCase):
    def test_run_equals_query_removed_from_public_api(self):
        import app.services.position_match as pm

        self.assertFalse(hasattr(pm, "run_equals_query"))


if __name__ == "__main__":
    unittest.main()
