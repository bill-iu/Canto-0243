"""Public preload /ready API — search acceleration UX."""

import unittest

from fastapi.testclient import TestClient

from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests
from main import app


class TestPreloadReadyEndpoint(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()

    def test_ready_false_before_word_cache_populated(self):
        client = TestClient(app)
        payload = client.get("/ready").json()
        self.assertFalse(payload["ready"])
        self.assertIn(payload["status"], ("pending", "loading"))

    def test_ready_true_after_word_cache_populated(self):
        populate_word_cache_from_rows([
            {
                "char": "做就",
                "code": "23",
                "jyutping": "zou6 zau6",
                "finals": '["ou","au"]',
                "initials": '["z","z"]',
                "length": 2,
            },
        ])
        complete_preload()
        client = TestClient(app)
        payload = client.get("/ready").json()
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["gate_ready"])
        self.assertEqual(payload["phases"]["word_cache"]["status"], "ready")
        self.assertIn("startup_complete", payload)
        self.assertIn("tail_pending", payload)


if __name__ == "__main__":
    unittest.main()
