"""Architecture #E — 近反義池投影收錄種子字面。"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.pool_projection import project_relation_pool


class PoolProjectionAdmissionTests(unittest.TestCase):
    @patch("app.services.word_ensure_service.ensure_word_in_db")
    def test_project_relation_pool_injects_seed_when_allowed(self, mock_ensure):
        mock_ensure.return_value = []
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        try:
            project_relation_pool(session, "開心", allow_inject=True)
            mock_ensure.assert_called_once_with(session, "開心")
        finally:
            session.close()

    @patch("app.services.word_ensure_service.ensure_word_in_db")
    def test_project_relation_pool_skips_inject_when_disabled(self, mock_ensure):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        try:
            project_relation_pool(session, "開心", allow_inject=False)
            mock_ensure.assert_not_called()
        finally:
            session.close()


class RelationSearchRemovalTests(unittest.TestCase):
    def test_relation_search_module_removed(self):
        import importlib.util

        spec = importlib.util.find_spec("app.services.relation_search")
        self.assertIsNone(spec)


class RelationExecutorAdmissionSeamTests(unittest.TestCase):
    def test_relation_syntax_executor_does_not_call_ensure(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "services"
            / "relation_syntax_executor.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("ensure_word_in_db", source)


if __name__ == "__main__":
    unittest.main()
