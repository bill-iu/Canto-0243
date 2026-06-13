"""Phase B: app/domain/relations — runtime 關係寫入不依賴 ingest。"""

import ast
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import insert_relation_candidates


REPO_ROOT = Path(__file__).resolve().parents[1]


class RelationDomainStoreTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_insert_relation_candidates_writes_canonical_row(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=10, char="快樂", code="22", jyutping="", length=2),
                Word(id=20, char="開心", code="22", jyutping="", length=2),
            ])
            db.commit()

            w, r = canonical_word_ids(10, 20)
            key = (w, r, "syn")
            inserted, skipped = insert_relation_candidates(
                db,
                {
                    key: {
                        "word_id": w,
                        "related_id": r,
                        "relation_type": "syn",
                        "score": 0.9,
                        "source": "test",
                    }
                },
                dedupe_existing=True,
                batch_size=50,
            )
            self.assertEqual(inserted, 1)
            self.assertEqual(skipped, 0)

            row = (
                db.query(WordRelation)
                .filter(
                    WordRelation.word_id == w,
                    WordRelation.related_id == r,
                    WordRelation.relation_type == "syn",
                )
                .one()
            )
            self.assertEqual(row.source, "test")

    def test_insert_relation_candidates_skips_existing(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="甲", code="22", jyutping="", length=1),
                Word(id=2, char="乙", code="22", jyutping="", length=1),
            ])
            db.add(
                WordRelation(
                    word_id=1,
                    related_id=2,
                    relation_type="ant",
                    score=0.8,
                    source="existing",
                )
            )
            db.commit()

            inserted, skipped = insert_relation_candidates(
                db,
                {
                    (1, 2, "ant"): {
                        "word_id": 1,
                        "related_id": 2,
                        "relation_type": "ant",
                        "score": 0.95,
                        "source": "new",
                    }
                },
                dedupe_existing=True,
                batch_size=50,
            )
            self.assertEqual(inserted, 0)
            self.assertEqual(skipped, 1)


class RuntimeNoIngestImportTests(unittest.TestCase):
    def _imports_ingest(self, module_path: Path) -> list[str]:
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        hits: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("ingest"):
                        hits.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("ingest"):
                    hits.append(node.module)
        return hits

    def test_manual_relation_service_does_not_import_ingest(self):
        path = REPO_ROOT / "app" / "services" / "manual_relation_service.py"
        self.assertEqual(self._imports_ingest(path), [])

    def test_compound_ant_executor_does_not_import_ingest(self):
        path = REPO_ROOT / "app" / "services" / "compound_ant_executor.py"
        self.assertEqual(self._imports_ingest(path), [])

    def test_compound_syn_executor_does_not_import_ingest(self):
        path = REPO_ROOT / "app" / "services" / "compound_syn_executor.py"
        self.assertEqual(self._imports_ingest(path), [])

    def test_word_model_uses_domain_canonical(self):
        path = REPO_ROOT / "app" / "models" / "word.py"
        self.assertEqual(self._imports_ingest(path), [])


if __name__ == "__main__":
    unittest.main()
