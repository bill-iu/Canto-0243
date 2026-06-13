import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.word import Word, WordRelation
from app.routers.word import get_db
from app.services.manual_relation_service import (
    ManualRelationError,
    create_creator_manual_relation,
    revoke_creator_manual_relation,
)
from app.services.syn_ant_service import search_syn_ant
from main import app


class RevokeCreatorManualRelationTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_revoke_removes_direct_and_expand_only_from_same_submit(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="愉快", code="22", jyutping="", length=2),
                Word(id=4, char="幸福", code="22", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=1, related_id=4, relation_type="syn", score=0.8, source="cilin"),
            ])
            db.commit()

            create_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )
            result = revoke_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )

            self.assertEqual(result, {"direct": 1, "expand": 1})
            self.assertEqual(db.query(WordRelation).filter(WordRelation.source == "manual").count(), 0)
            self.assertEqual(
                db.query(WordRelation).filter(WordRelation.source == "manual_syn_cluster").count(),
                0,
            )
            self.assertEqual(db.query(WordRelation).filter(WordRelation.source == "cilin").count(), 2)

    def test_revoke_does_not_delete_cilin_direct(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="不幸", code="22", jyutping="", length=2),
                Word(id=2, char="好運", code="22", jyutping="", length=2),
            ])
            db.add(
                WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.9, source="cilin")
            )
            db.commit()

            with self.assertRaises(ManualRelationError) as ctx:
                revoke_creator_manual_relation(
                    db, seed_char="不幸", opposite_char="好運", relation_type="syn"
                )
            self.assertEqual(ctx.exception.code, "not_found")
            self.assertEqual(db.query(WordRelation).count(), 1)

    def test_revoke_syn_updates_relation_search(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="不幸", code="22", jyutping="", length=2),
                Word(id=2, char="好運", code="22", jyutping="", length=2),
            ])
            db.commit()

            create_creator_manual_relation(
                db, seed_char="不幸", opposite_char="好運", relation_type="syn"
            )
            syns_before = {
                r["char"]
                for r in search_syn_ant(db, "不幸", include_static=False)
                if r["relation"] == "syn"
            }
            self.assertIn("好運", syns_before)

            revoke_creator_manual_relation(
                db, seed_char="不幸", opposite_char="好運", relation_type="syn"
            )
            syns_after = {
                r["char"]
                for r in search_syn_ant(db, "不幸", include_static=False)
                if r["relation"] == "syn"
            }
            self.assertNotIn("好運", syns_after)


class RevokeManualRelationApiTests(unittest.TestCase):
    def _client(self):
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
        self.addCleanup(app.dependency_overrides.clear)
        return TestClient(app), Session

    def test_api_revoke_returns_count_summary(self):
        client, Session = self._client()
        with Session() as db:
            db.add_all([
                Word(id=1, char="不幸", code="22", jyutping="", length=2),
                Word(id=2, char="好運", code="22", jyutping="", length=2),
            ])
            db.commit()

        client.post(
            "/relations/manual",
            json={
                "seed_char": "不幸",
                "opposite_char": "好運",
                "relation_type": "syn",
            },
        )
        response = client.post(
            "/relations/manual/revoke",
            json={
                "seed_char": "不幸",
                "opposite_char": "好運",
                "relation_type": "syn",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["direct"], 1)
        self.assertIn("已撤回", payload["message"])


if __name__ == "__main__":
    unittest.main()
