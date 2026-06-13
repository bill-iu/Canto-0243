"""Phase C #5: execute_search returns SearchResult with total (no global state)."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import SearchContext, execute_search


class ExecuteSearchResultTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def test_pure_digit_search_returns_total_in_result(self):
        with self.Session() as db:
            for i in range(5):
                db.add(
                    Word(
                        char=f"詞{i}",
                        code="33",
                        jyutping="ci4 zi6",
                        finals='["i"]',
                        initials='["z"]',
                        length=2,
                    )
                )
            db.commit()

            out = execute_search(
                SearchContext(q="33", code=None, char=None, mode="m1", limit=2, offset=0, db=db)
            )
            self.assertEqual(len(out.items), 2)
            self.assertEqual(out.total, 5)

    def test_query_parse_module_has_no_db_import(self):
        import ast
        from pathlib import Path

        tree = ast.parse(
            Path("app/services/query_parse.py").read_text(encoding="utf-8")
        )
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("sqlalchemy", alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn("sqlalchemy", node.module)


if __name__ == "__main__":
    unittest.main()
