"""參考字讀音解析 — inject port 行為（ADR-0004 #2）。"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.lexicon.reference_reading import anchor_phoneme_options


class ReferenceReadingInjectPortTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_allow_inject_false_does_not_call_inject_port(self):
        port = MagicMock()
        with patch(
            "app.domain.lexicon.reference_reading.default_word_inject_port",
            return_value=port,
        ):
            with self.Session() as db:
                anchor_phoneme_options("香", "final", db, allow_inject=False)
        port.ensure_word_rows.assert_not_called()
        port.inject_lexicon_rows.assert_not_called()

    def test_allow_inject_true_calls_ensure_when_db_empty_and_admission_allows(self):
        port = MagicMock()
        port.ensure_word_rows.return_value = []
        with patch(
            "app.domain.lexicon.reference_reading.default_word_inject_port",
            return_value=port,
        ):
            with patch(
                "app.domain.lexicon.reference_reading.resolve_admission"
            ) as resolve:
                resolve.return_value = MagicMock(
                    entries=[], can_inject=True
                )
                with self.Session() as db:
                    anchor_phoneme_options("測", "final", db, allow_inject=True)
        port.ensure_word_rows.assert_called_once()


if __name__ == "__main__":
    unittest.main()
