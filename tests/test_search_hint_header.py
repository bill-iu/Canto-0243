"""X-Search-Hint RFC 5987 header encoding."""
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.utils.search_hint_header import decode_search_hint, encode_search_hint
from main import app


class SearchHintHeaderTests(unittest.TestCase):
    def test_roundtrip_non_ascii(self):
        raw = "「更好」有收錄，但在 0243 碼 23 下無整詞同韻結果。"
        encoded = encode_search_hint(raw)
        self.assertTrue(encoded.isascii())
        self.assertEqual(decode_search_hint(encoded), raw)

    def test_ascii_passthrough(self):
        self.assertEqual(encode_search_hint("m1 redirect"), "m1 redirect")

    def test_search_endpoint_sets_encoded_hint(self):
        client = TestClient(app)
        res = client.get(
            "/words/search/",
            params={"q": "0999窮困潦倒=", "mode": "m1", "limit": 5},
        )
        self.assertEqual(res.status_code, 200)
        hint = res.headers.get("X-Search-Hint")
        self.assertIsNotNone(hint)
        self.assertTrue(hint.isascii())
        decoded = decode_search_hint(hint)
        self.assertIn("窮困潦倒", decoded)


if __name__ == "__main__":
    unittest.main()
