"""query explain for new $ / $$ / heteronym syntax."""
import unittest

from app.services.query_explain import explain_query


class QueryExplainNewSyntaxTests(unittest.TestCase):
    def test_doubled_dollar_summary(self):
        r = explain_query("$$", "m1")
        self.assertIn("同音節疊字", r.summary or "")

    def test_heteronym_summary(self):
        r = explain_query("33/34", "m1")
        self.assertIn("異讀", r.summary or "")
        self.assertIn("33/34", r.summary or "")


if __name__ == "__main__":
    unittest.main()
