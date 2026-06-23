"""有效字面規則與近反義池過濾回歸測試。"""

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.valid_term import clean_term, is_valid_term, normalize_literal
from app.domain.thesaurus.port import StaticThesaurusPort
from app.services.relation_syntax_executor import RelationSyntaxExecutor


class ValidTermTests(unittest.TestCase):
    def test_rejects_cilin_code_token(self):
        self.assertIsNone(normalize_literal("Hi10C02#"))

    def test_clean_term_strips_parenthetical(self):
        self.assertEqual(clean_term("開心（愉快）"), "開心")
        self.assertTrue(is_valid_term(clean_term("開心（愉快）")))

    def test_normalize_literal_converts_simplified_to_traditional(self):
        self.assertEqual(normalize_literal("快乐"), "快樂")
        self.assertEqual(normalize_literal("高兴"), "高興")
        self.assertEqual(normalize_literal("开心"), "開心")


class GuotongNoiseFixtureTests(unittest.TestCase):
    def tearDown(self) -> None:
        from app.domain.thesaurus.port import default_thesaurus_port
        from app.thesaurus.static_index import ensure_thesaurus_loaded, reset_static_indexes_for_tests
        from app.utils.word_cache import reset_word_cache_for_tests

        reset_word_cache_for_tests()
        reset_static_indexes_for_tests()
        ensure_thesaurus_loaded(force=True)
        default_thesaurus_port()._loaded = False  # type: ignore[attr-defined]

    def test_static_load_skips_cilin_code_in_guotong_file(self):
        fixtures = Path(__file__).resolve().parents[1] / "data" / "syn_ant" / "fixtures"
        port = StaticThesaurusPort(
            thesaurus_syn_path=str(fixtures / "guotong_noise_sample.txt"),
            thesaurus_ant_path=str(fixtures / "antonym_sample.txt"),
            auto_load=True,
        )
        syns = port.get_guotong_synonyms("你好")
        self.assertIn("您好", syns)
        self.assertNotIn("Hi10C02#", syns)
        self.assertNotIn("Hi10C02#", set(port.iter_literal_heads()))

    def test_syn_mode_pool_excludes_cilin_code_for_ni_hao(self):
        fixtures = Path(__file__).resolve().parents[1] / "data" / "syn_ant" / "fixtures"
        port = StaticThesaurusPort(
            thesaurus_syn_path=str(fixtures / "guotong_noise_sample.txt"),
            thesaurus_ant_path=str(fixtures / "antonym_sample.txt"),
            auto_load=True,
        )
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        page = RelationSyntaxExecutor(session, thesaurus=port).syn_mode_page(
            "你好", limit=50, offset=0
        )
        chars = [r.get("char") for r in page]
        self.assertNotIn("Hi10C02#", chars)
        self.assertIn("您好", chars)


if __name__ == "__main__":
    unittest.main()
