"""apply_match_spec 單管線 smoke（每 MatchSpec 家族一條）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.position_match.engine import PositionMatchEngine
from app.services.position_match.filters import apply_match_spec
from app.services.position_match.sources import get_candidates_for_length
from app.services.query_parse import normalize_and_parse, normalize_to_match_spec
from app.services.word_serializer import get_word_text


class ApplyMatchSpecPipelineTests(unittest.TestCase):
    def _session(self, words: list[Word]):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all(words)
        session.commit()
        return session

    def _rows_for_spec(self, spec, session):
        if spec.ref_literal:
            return apply_match_spec(spec, [], session, "m1")
        candidates, _ = get_candidates_for_length(
            session, spec.width, code=spec.code_prefix, mode="m1"
        )
        return apply_match_spec(spec, candidates, session, "m1")

    def test_apply_match_spec_smoke_matrix(self):
        seeds = [
            Word(
                char="香港",
                code="33",
                jyutping="hoeng1 gong2",
                finals='["oeng","ong"]',
                initials='["h","g"]',
                length=2,
            ),
            Word(
                char="門口",
                code="10",
                jyutping="mun4 hau2",
                finals='["un","au"]',
                initials='["m","h"]',
                length=2,
            ),
            Word(
                char="好我",
                code="34",
                jyutping="hou2 ngo5",
                finals='["ou","o"]',
                initials='["h","ng"]',
                length=2,
            ),
        ]
        cases = [
            ("香港=", lambda chars: "香港" in chars),
            ("門0", lambda chars: "門口" in chars),
            ("34=我", lambda chars: "好我" in chars),
        ]
        session = self._session(seeds)
        try:
            for q, check in cases:
                with self.subTest(q=q):
                    spec = normalize_to_match_spec(normalize_and_parse(q))
                    self.assertIsNotNone(spec)
                    rows = self._rows_for_spec(spec, session)
                    chars = [get_word_text(w) for w in rows]
                    self.assertTrue(check(chars), msg=f"{q!r} -> {chars}")
        finally:
            session.close()

    def test_engine_delegates_to_apply_match_spec(self):
        session = self._session(
            [
                Word(
                    char="好我",
                    code="34",
                    jyutping="hou2 ngo5",
                    finals='["ou","o"]',
                    initials='["h","ng"]',
                    length=2,
                ),
            ]
        )
        try:
            spec = normalize_to_match_spec(normalize_and_parse("34=我"))
            self.assertIsNotNone(spec)
            candidates, _ = get_candidates_for_length(
                session, spec.width, code=spec.code_prefix, mode="m1"
            )
            direct = apply_match_spec(spec, candidates, session, "m1")
            via_engine = PositionMatchEngine().match(
                spec, None, session, "m1", pre_candidates=candidates
            )
            self.assertEqual(
                sorted(get_word_text(w) for w in direct),
                sorted(get_word_text(w) for w in via_engine),
            )
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
