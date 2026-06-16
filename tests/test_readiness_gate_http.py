"""就緒閘 HTTP：503 flat snapshot 與 /ready 契約一致。"""
from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from app.startup.offline_preload import reset_background_preload_state_for_tests
from app.startup.readiness_gate import reset_readiness_gate_for_tests, snapshot
from app.utils.word_cache import complete_preload, reset_word_cache_for_tests
from main import app


class ReadinessGateHttpTests(unittest.TestCase):
    def setUp(self):
        os.environ["READINESS_GATE_ENFORCE"] = "1"
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()
        reset_readiness_gate_for_tests()

    def tearDown(self):
        os.environ.pop("READINESS_GATE_ENFORCE", None)
        reset_word_cache_for_tests()
        reset_background_preload_state_for_tests()
        reset_readiness_gate_for_tests()

    def test_search_returns_503_with_flat_snapshot_while_locked(self):
        client = TestClient(app)
        expected = snapshot()
        res = client.get("/words/search/?q=23")
        self.assertEqual(res.status_code, 503)
        self.assertEqual(res.headers.get("retry-after"), "1")
        body = res.json()
        self.assertFalse(body["gate_ready"])
        self.assertIn("word_cache_progress", body)
        self.assertEqual(body["gate_ready"], expected["gate_ready"])

    def test_empty_query_returns_503_while_locked(self):
        client = TestClient(app)
        for path in ("/words/search/", "/words/search/?code=33"):
            with self.subTest(path=path):
                res = client.get(path)
                self.assertEqual(res.status_code, 503)
                self.assertEqual(res.headers.get("retry-after"), "1")
                self.assertFalse(res.json()["gate_ready"])

    def test_search_allowed_after_gate_opens(self):
        complete_preload()
        client = TestClient(app)
        res = client.get("/words/search/?q=23")
        self.assertNotEqual(res.status_code, 503)

    def test_empty_query_allowed_after_gate_opens(self):
        complete_preload()
        client = TestClient(app)
        res = client.get("/words/search/", params={"code": "33", "limit": 5})
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_ready_and_503_share_schema_fields(self):
        client = TestClient(app)
        ready = client.get("/ready").json()
        blocked = client.get("/words/search/?q=23").json()
        for key in ("gate_ready", "degraded", "gate_open_reason", "word_cache_progress", "phases"):
            self.assertIn(key, ready)
            self.assertIn(key, blocked)


if __name__ == "__main__":
    unittest.main()
