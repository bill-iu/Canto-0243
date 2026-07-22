from __future__ import annotations

from itertools import product
from unittest.mock import patch
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.routers.word import get_db
from app.routers.workbench import router
from app.schemas.workbench_schema import CandidateGroups, WorkbenchCandidateResponse
from app.models.word import Word


class WorkbenchApiSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            db.add(Word(char="香", code="3", jyutping="hoeng1", length=1))
            db.commit()
        app = FastAPI()
        app.include_router(router)

        def override_db():
            with self.Session() as db:
                yield db

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_readings_endpoint_is_thin_and_non_writing(self) -> None:
        response = self.client.post("/workbench/readings", json={"surface": "香，"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["choices"][0]["jyutping"], "hoeng1")
        self.assertEqual(response.json()[1]["kind"], "punctuation")

    def test_candidates_validates_plan_and_never_returns_applied_lyrics(self) -> None:
        empty = WorkbenchCandidateResponse(
            selection_version=4,
            exact=CandidateGroups(direct_syn=[], semantic_related=[], sound_only=[]),
            total=0,
        )
        plan = {
            "version": 1,
            "selectionVersion": 4,
            "width": 1,
            "mode": "m3",
            "slots": [{"pos": 0, "kind": "code_digit", "digit": "3"}],
            "semanticIntent": "off",
            "limit": 20,
        }
        with patch("app.routers.workbench.plan_replacements", return_value=empty):
            response = self.client.post("/workbench/candidates", json=plan)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("lyrics", response.json())
        self.assertNotIn("applied", response.json())

        # ADR-0069: width 5–64 valid; only above line max rejected
        plan["width"] = 5
        self.assertEqual(self.client.post("/workbench/candidates", json=plan).status_code, 200)
        plan["width"] = 65
        self.assertEqual(self.client.post("/workbench/candidates", json=plan).status_code, 422)

    def test_candidates_unanchored_width_scan_returns_paginated_pool(self) -> None:
        with self.Session() as db:
            alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
            literals = ["".join(pair) for pair in product(alphabet, repeat=2)][:2001]
            db.add_all(
                Word(char=literal, code="12", jyutping="gaa1", length=2)
                for literal in literals
            )
            db.commit()

        plan = {
            "version": 1,
            "selectionVersion": 9,
            "width": 2,
            "mode": "m1",
            "slots": [],
            "semanticIntent": "off",
            "limit": 1,
            "offset": 0,
        }
        first = self.client.post("/workbench/candidates", json=plan)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["engineTotal"], 2001)
        self.assertEqual(len(first.json()["exact"]["sound_only"]), 1)

        plan["offset"] = 2000
        second = self.client.post("/workbench/candidates", json=plan)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["engineTotal"], 2001)
        self.assertEqual(len(second.json()["exact"]["sound_only"]), 1)


if __name__ == "__main__":
    unittest.main()
