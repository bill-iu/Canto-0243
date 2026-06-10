import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.routers.word import _build_character_search_results, search_words


class CharacterDetailPayloadTests(unittest.TestCase):
    def test_build_character_search_results(self):
        words = [
            SimpleNamespace(char="字", code="23", jyutping="zi6"),
            SimpleNamespace(char="子", code="23", jyutping="zi2"),
            SimpleNamespace(char="自", code="23", jyutping="zi6"),
        ]

        payload = _build_character_search_results("字", words)

        self.assertEqual(payload[0]["display_text"], "23")
        self.assertEqual(payload[0]["code"], "23")
        self.assertEqual(payload[0]["jyutping"], "")
        self.assertEqual(payload[1]["display_text"], "zi6")
        self.assertEqual(payload[1]["code"], "")
        self.assertEqual(payload[2]["display_text"], "zi2")
        self.assertTrue(any(item["display_text"] == "子" for item in payload))
        self.assertTrue(any(item["display_text"] == "自" for item in payload))

    def test_search_words_for_mixed_character_query(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with TestingSession() as session:
            session.add_all([
                Word(char="A仔", code="23", jyutping="aa1 zai2", length=2),
                Word(char="B仔", code="23", jyutping="bei2 zai2", length=2),
            ])
            session.commit()

            results = search_words(q="A仔", db=session, limit=20, offset=0)

        word_results = [item for item in results if item["result_type"] == "word"]
        self.assertTrue(any(item["char"] == "A仔" for item in word_results))
        self.assertTrue(any(item["char"] == "B仔" for item in word_results))
        self.assertEqual(word_results[0]["char"], "A仔")

    def test_same_rhyme_words_rank_before_different_rhyme_words(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with TestingSession() as session:
            session.add_all([
                Word(char="做到", code="24", jyutping="zou6 dou3", finals="[\"ou\", \"ou\"]", initials="[\"z\", \"d\"]", length=2),
                Word(char="做數", code="", jyutping="zou6 sou3", finals="[\"ou\", \"ou\"]", initials="[\"z\", \"s\"]", length=2),
                Word(char="路數", code="", jyutping="lou6 sou3", finals="[\"ou\", \"ou\"]", initials="[\"l\", \"s\"]", length=2),
                Word(char="丈母", code="", jyutping="zoeng6 mou5", finals="[\"oeng\", \"ou\"]", initials="[\"z\", \"m\"]", length=2),
                Word(char="䀹嘢", code="", jyutping="gap6 je5", finals="[\"ap\", \"e\"]", initials="[\"g\", \"j\"]", length=2),
            ])
            session.commit()

            results = search_words(q="做到", db=session, limit=20, offset=0)
            word_results = [item for item in results if item["result_type"] == "word"]

        self.assertEqual(word_results[0]["char"], "做到")
        self.assertEqual(word_results[1]["char"], "做數")
        self.assertTrue(word_results.index(next(item for item in word_results if item["char"] == "做數")) < word_results.index(next(item for item in word_results if item["char"] == "路數")))
        self.assertTrue(word_results.index(next(item for item in word_results if item["char"] == "路數")) < word_results.index(next(item for item in word_results if item["char"] == "丈母")))
        self.assertTrue(word_results.index(next(item for item in word_results if item["char"] == "路數")) < word_results.index(next(item for item in word_results if item["char"] == "䀹嘢")))


if __name__ == "__main__":
    unittest.main()
