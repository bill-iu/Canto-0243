"""詞庫勘誤介面 API（public interface）。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.word import Word
from app.routers.lexicon import get_corrections_path
from app.routers.word import get_db
from ingest.lexicon_corrections import load_corrections

from main import app


class LexiconCorrectionApiTests(unittest.TestCase):
    def _client(self, *, tsv_path: Path):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        def override_get_db():
            db = Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_corrections_path] = lambda: tsv_path
        self.addCleanup(app.dependency_overrides.clear)
        return TestClient(app), Session

    def test_list_word_rows_for_char(self):
        with tempfile.TemporaryDirectory() as tmp:
            client, Session = self._client(tsv_path=Path(tmp) / "c.tsv")
            with Session() as db:
                db.add_all([
                    Word(id=1, char="不斷", code="34", jyutping="but1 dyun6", length=2),
                    Word(id=2, char="不斷", code="32", jyutping="but1 dyun6", length=2),
                ])
                db.commit()

            response = client.get("/words/rows", params={"char": "不斷"})
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(len(payload), 2)
            codes = {row["code"] for row in payload}
            self.assertEqual(codes, {"34", "32"})

    def test_queue_correction_appends_pending_tsv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tsv_path = Path(tmp) / "c.tsv"
            client, _Session = self._client(tsv_path=tsv_path)

            response = client.post(
                "/lexicon/corrections",
                json={
                    "char": "不斷",
                    "code": "34",
                    "jyutping": "but1 dyun6",
                    "action": "set_code",
                    "value": "32",
                    "note": "編碼混入 tyun5",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["pending_count"], 1)
            self.assertIn("已記錄", payload["message"])

            rows = load_corrections(tsv_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].char, "不斷")
            self.assertEqual(rows[0].old_code, "34")
            self.assertEqual(rows[0].action, "set_code")
            self.assertEqual(rows[0].value, "32")

    def test_queue_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tsv_path = Path(tmp) / "c.tsv"
            client, _Session = self._client(tsv_path=tsv_path)
            payload = {
                "char": "不斷",
                "code": "34",
                "jyutping": "but1 dyun6",
                "action": "set_code",
                "value": "32",
                "note": "",
            }
            first = client.post("/lexicon/corrections", json=payload)
            self.assertEqual(first.status_code, 200)

            second = client.post("/lexicon/corrections", json=payload)
            self.assertEqual(second.status_code, 409)
            self.assertIn("相同", second.json()["detail"])

            rows = load_corrections(tsv_path)
            self.assertEqual(len(rows), 1)

    def test_preview_code_from_jyutping(self):
        with tempfile.TemporaryDirectory() as tmp:
            client, _Session = self._client(tsv_path=Path(tmp) / "c.tsv")
            response = client.get("/lexicon/code-preview", params={"jyutping": "but1 dyun6"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["code"], "32")


if __name__ == "__main__":
    unittest.main()
