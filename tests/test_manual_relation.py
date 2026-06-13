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
    prune_conflicting_manual_expansions,
)
from app.services.relation_search import search_syn_ant
from main import app


class CreatorManualRelationTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def test_syn_direct_when_opposite_has_no_syn_neighbors(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
                Word(id=2, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            ])
            db.commit()

            result = create_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )

            self.assertEqual(result, {"direct": 1, "expand": 0, "skipped": 0})
            rows = db.query(WordRelation).filter(WordRelation.source == "manual").all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].relation_type, "syn")
            self.assertAlmostEqual(rows[0].score, 0.95)

    def test_syn_cluster_one_hop_from_opposite(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="愉快", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.9, source="cilin"))
            db.commit()

            result = create_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )

            self.assertEqual(result["direct"], 1)
            self.assertEqual(result["expand"], 1)
            self.assertEqual(result["skipped"], 0)
            expanded = (
                db.query(WordRelation)
                .filter(WordRelation.source == "manual_syn_cluster")
                .all()
            )
            self.assertEqual(len(expanded), 1)
            self.assertAlmostEqual(expanded[0].score, 0.82)

    def test_ant_mirror_one_hop_from_opposite_syns(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="悲傷", code="22", jyutping="", length=2),
                Word(id=3, char="傷心", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.9, source="cilin"))
            db.commit()

            result = create_creator_manual_relation(
                db, seed_char="快樂", opposite_char="悲傷", relation_type="ant"
            )

            self.assertEqual(result["direct"], 1)
            self.assertEqual(result["expand"], 1)
            mirror = (
                db.query(WordRelation)
                .filter(WordRelation.source == "manual_ant_mirror", WordRelation.relation_type == "ant")
                .all()
            )
            self.assertEqual(len(mirror), 1)

    def test_rejects_when_direct_already_exists(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.add(
                WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.9, source="cilin")
            )
            db.commit()

            with self.assertRaises(ManualRelationError) as ctx:
                create_creator_manual_relation(
                    db, seed_char="快樂", opposite_char="開心", relation_type="syn"
                )
            self.assertEqual(ctx.exception.code, "already_exists")
            self.assertEqual(db.query(WordRelation).count(), 1)

    def test_rejects_when_literal_not_in_lexicon(self):
        Session = self._session()
        with Session() as db:
            db.add(Word(id=1, char="快樂", code="22", jyutping="", length=2))
            db.commit()

            with self.assertRaises(ManualRelationError) as ctx:
                create_creator_manual_relation(
                    db, seed_char="快樂", opposite_char="開心", relation_type="syn"
                )
            self.assertEqual(ctx.exception.code, "not_in_lexicon")

    def test_expand_skips_existing_rows(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="愉快", code="22", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.8, source="cilin"),
            ])
            db.commit()

            result = create_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )

            self.assertEqual(result["direct"], 1)
            self.assertEqual(result["expand"], 0)
            self.assertEqual(result["skipped"], 1)

    def test_ant_mirror_skips_seed_existing_syns(self):
        """羞恥 ant 無恥 must not mirror 丟人/丟臉 as ant when they are already syns of 羞恥."""
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="羞恥", code="22", jyutping="", length=2),
                Word(id=2, char="無恥", code="22", jyutping="", length=2),
                Word(id=3, char="丟人", code="22", jyutping="", length=2),
                Word(id=4, char="丟臉", code="22", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=1, related_id=4, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=2, related_id=4, relation_type="syn", score=0.9, source="cilin"),
            ])
            db.commit()

            result = create_creator_manual_relation(
                db, seed_char="羞恥", opposite_char="無恥", relation_type="ant"
            )

            self.assertEqual(result["direct"], 1)
            self.assertEqual(result["expand"], 0)
            mirror = (
                db.query(WordRelation)
                .filter(
                    WordRelation.source == "manual_ant_mirror",
                    WordRelation.relation_type == "ant",
                )
                .all()
            )
            self.assertEqual(len(mirror), 0)

            res = search_syn_ant(db, "羞恥", include_static=False)
            syns = {r["char"] for r in res if r["relation"] == "syn"}
            ants = {r["char"] for r in res if r["relation"] == "ant"}
            self.assertIn("丟人", syns)
            self.assertIn("丟臉", syns)
            self.assertIn("無恥", ants)
            self.assertNotIn("丟人", ants)
            self.assertNotIn("丟臉", ants)
            self.assertFalse(syns & ants)

    def test_prune_conflicting_manual_expansions(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="羞恥", code="22", jyutping="", length=2),
                Word(id=2, char="無恥", code="22", jyutping="", length=2),
                Word(id=3, char="丟人", code="22", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=1, related_id=2, relation_type="ant", score=0.95, source="manual"),
                WordRelation(
                    word_id=1,
                    related_id=3,
                    relation_type="ant",
                    score=0.82,
                    source="manual_ant_mirror",
                ),
            ])
            db.commit()

            stats = prune_conflicting_manual_expansions(db, seed_char="羞恥")
            self.assertEqual(stats["removed"], 1)
            remaining = (
                db.query(WordRelation)
                .filter(WordRelation.source == "manual_ant_mirror")
                .count()
            )
            self.assertEqual(remaining, 0)

    def test_prune_conflicting_manual_expansions_canonical_order(self):
        """Canonical storage puts smaller word id in word_id — prune must still find conflicts."""
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="丟人", code="22", jyutping="", length=2),
                Word(id=2, char="羞恥", code="22", jyutping="", length=2),
                Word(id=3, char="無恥", code="22", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.9, source="cilin"),
                WordRelation(word_id=3, related_id=2, relation_type="ant", score=0.95, source="manual"),
                WordRelation(
                    word_id=1,
                    related_id=2,
                    relation_type="ant",
                    score=0.82,
                    source="manual_ant_mirror",
                ),
            ])
            db.commit()

            stats = prune_conflicting_manual_expansions(db, seed_char="羞恥")
            self.assertEqual(stats["removed"], 1)
            self.assertEqual(
                db.query(WordRelation)
                .filter(WordRelation.source == "manual_ant_mirror")
                .count(),
                0,
            )

    def test_manual_syn_visible_in_relation_search(self):
        Session = self._session()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.commit()

            create_creator_manual_relation(
                db, seed_char="快樂", opposite_char="開心", relation_type="syn"
            )
            syns = [r["char"] for r in search_syn_ant(db, "快樂", include_static=False) if r["relation"] == "syn"]
            self.assertIn("開心", syns)


class ManualRelationApiTests(unittest.TestCase):
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

    def test_api_returns_count_summary(self):
        client, Session = self._client()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.commit()

        response = client.post(
            "/relations/manual",
            json={
                "seed_char": "快樂",
                "opposite_char": "開心",
                "relation_type": "syn",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["direct"], 1)
        self.assertIn("已新增", payload["message"])

    def test_api_conflict_when_relation_exists(self):
        client, Session = self._client()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
            ])
            db.add(WordRelation(word_id=1, related_id=2, relation_type="syn", source="cilin"))
            db.commit()

        response = client.post(
            "/relations/manual",
            json={
                "seed_char": "快樂",
                "opposite_char": "開心",
                "relation_type": "syn",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("已存在", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
