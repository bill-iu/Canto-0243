from __future__ import annotations

import unittest

from app.models.word import Word
from app.schemas.workbench_schema import ReplacementPlanV1
from app.services.workbench.candidate_snapshot import CandidateSnapshotStore
from app.services.workbench.replacement_planner import plan_replacements
from tests.smoke.helpers import memory_sessionmaker, seed_happy_sad


def make_plan(*, offset: int = 0, selection_version: int = 1) -> ReplacementPlanV1:
    return ReplacementPlanV1.model_validate({
        "version": 1,
        "selectionVersion": selection_version,
        "width": 2,
        "mode": "m1",
        "slots": [],
        "semanticIntent": "off",
        "limit": 2,
        "offset": offset,
    })


class CandidateSnapshotStoreTests(unittest.TestCase):
    @staticmethod
    def literals(response) -> list[str]:
        return [
            *[item.literal for item in response.exact.direct_syn],
            *[item.literal for item in response.exact.semantic_related],
            *[item.literal for item in response.exact.sound_only],
        ]

    def test_same_handle_pages_one_immutable_candidate_pool(self) -> None:
        Session = memory_sessionmaker()
        store = CandidateSnapshotStore()
        with Session() as db:
            db.add_all([
                Word(char="乙乙", jyutping="jat1 jat1", code="11", length=2),
                Word(char="丙丙", jyutping="bing2 bing2", code="11", length=2),
                Word(char="丁丁", jyutping="ding1 ding1", code="11", length=2),
            ])
            db.commit()

            first = store.page(make_plan(), db)
            db.add(Word(char="甲甲", jyutping="gaa1 gaa1", code="11", length=2))
            db.commit()
            second = store.page(
                make_plan(offset=2, selection_version=2),
                db,
                snapshot_id=first.snapshot_id,
            )
            fresh = store.page(make_plan(), db)

        self.assertEqual(first.response.engine_total, 3)
        self.assertEqual(second.response.engine_total, 3)
        self.assertEqual(second.response.selection_version, 2)
        paged_literals = {
            *[item.literal for item in first.response.exact.sound_only],
            *[item.literal for item in second.response.exact.sound_only],
        }
        self.assertEqual(paged_literals, {"乙乙", "丙丙", "丁丁"})
        self.assertEqual(fresh.response.engine_total, 4)
        self.assertNotEqual(fresh.snapshot_id, first.snapshot_id)

    def test_snapshot_pages_preserve_existing_semantic_page_order(self) -> None:
        Session = memory_sessionmaker()
        store = CandidateSnapshotStore()
        with Session() as db:
            seed_happy_sad(db)
            base = make_plan().model_copy(update={
                "semantic_intent": "ranked",
                "semantic_seed": "快樂",
                "slots": [],
                "limit": 1,
            })
            expected = [
                self.literals(plan_replacements(base.model_copy(update={"offset": offset}), db))
                for offset in range(3)
            ]
            first = store.page(base, db)
            actual = [self.literals(first.response)]
            for offset in range(1, 3):
                page = store.page(
                    base.model_copy(update={"offset": offset}),
                    db,
                    snapshot_id=first.snapshot_id,
                )
                actual.append(self.literals(page.response))

        self.assertEqual(actual, expected)

    def test_missing_handle_rebuilds_from_first_page_atomically(self) -> None:
        Session = memory_sessionmaker()
        store = CandidateSnapshotStore()
        with Session() as db:
            db.add_all([
                Word(char="乙乙", jyutping="jat1 jat1", code="11", length=2),
                Word(char="丙丙", jyutping="bing2 bing2", code="11", length=2),
                Word(char="丁丁", jyutping="ding1 ding1", code="11", length=2),
            ])
            db.commit()
            rebuilt = store.page(make_plan(offset=2), db, snapshot_id="expired")

        self.assertTrue(rebuilt.restarted)
        self.assertEqual(len(rebuilt.response.exact.sound_only), 2)
        self.assertEqual(rebuilt.response.engine_total, 3)

    def test_idle_snapshot_expires_after_ten_minutes(self) -> None:
        now = [0.0]
        Session = memory_sessionmaker()
        store = CandidateSnapshotStore(clock=lambda: now[0])
        with Session() as db:
            db.add(Word(char="乙乙", jyutping="jat1 jat1", code="11", length=2))
            db.commit()
            first = store.page(make_plan(), db)
            now[0] = 601.0
            expired = store.page(
                make_plan(offset=1),
                db,
                snapshot_id=first.snapshot_id,
            )

        self.assertTrue(expired.restarted)
        self.assertNotEqual(expired.snapshot_id, first.snapshot_id)

    def test_budget_evicts_oldest_snapshot_but_keeps_current(self) -> None:
        now = [0.0]
        Session = memory_sessionmaker()
        store = CandidateSnapshotStore(max_bytes=1, clock=lambda: now[0])
        with Session() as db:
            db.add_all([
                Word(char="香", jyutping="hoeng1", code="3", length=1),
                Word(char="乙乙", jyutping="jat1 jat1", code="11", length=2),
            ])
            db.commit()
            first = store.page(make_plan(), db)
            now[0] = 1.0
            current = store.page(make_plan().model_copy(update={"width": 1}), db)
            evicted = store.page(
                make_plan(offset=1),
                db,
                snapshot_id=first.snapshot_id,
            )

        self.assertFalse(current.restarted)
        self.assertTrue(evicted.restarted)

    def test_reused_relaxation_targets_current_draft_version(self) -> None:
        Session = memory_sessionmaker()
        store = CandidateSnapshotStore()
        plan = ReplacementPlanV1.model_validate({
            "version": 1,
            "selectionVersion": 1,
            "width": 1,
            "mode": "m3",
            "slots": [{"pos": 0, "kind": "code_digit", "digit": "3"}],
            "semanticIntent": "off",
            "limit": 2,
            "offset": 0,
        })
        with Session() as db:
            db.add(Word(char="香", jyutping="hoeng2", code="9", length=1))
            db.commit()
            first = store.page(plan, db)
            rebound = store.page(
                plan.model_copy(update={"selection_version": 2}),
                db,
                snapshot_id=first.snapshot_id,
            )

        self.assertIsNotNone(rebound.response.relaxation)
        self.assertEqual(rebound.response.relaxation.plan.selection_version, 2)


if __name__ == "__main__":
    unittest.main()
