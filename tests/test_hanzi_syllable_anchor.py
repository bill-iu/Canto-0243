"""漢字完整音節錨（$漢）— 行為測試（CONTEXT § 漢字完整音節錨）。"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_lexer import normalize_search_query
from app.services.query_parse import JyutpingAnchorQuery, parse_query


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class HanziDollarSyllableAnchorTests(unittest.TestCase):
    def test_3_dollar_hon4_normalizes_like_latin_anchor(self):
        self.assertEqual(normalize_search_query("3$漢4"), "3hon4")

    def test_3_dollar_hon4_parses_as_jyutping_anchor(self):
        parsed = _parse("3$漢4")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertEqual(parsed.anchor_value, "hon")
        self.assertEqual(parsed.width, 2)

    def test_3_dollar_hon4_search_matches_3hon4(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="韓流",
                        code="34",
                        jyutping="hon3 lau4",
                        finals='["on","au"]',
                        initials='["h","l"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="香爐",
                        code="34",
                        jyutping="hoeng1 lou4",
                        finals='["oeng","ou"]',
                        initials='["h","l"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            dollar = search_words(q="3$漢4", mode="m1", db=session, limit=20, offset=0)
            latin = search_words(q="3hon4", mode="m1", db=session, limit=20, offset=0)

        self.assertEqual([r["char"] for r in dollar], [r["char"] for r in latin])
        self.assertIn("韓流", [r["char"] for r in dollar])
        self.assertNotIn("香爐", [r["char"] for r in dollar])


if __name__ == "__main__":
    unittest.main()
