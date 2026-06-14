import unittest

from scripts.gen_readme_zh_hans import generate
from scripts.readme_zh_hans_written import find_colloquial_markers


class GenReadmeZhHansTests(unittest.TestCase):
    def test_generate_has_no_colloquial_markers(self):
        text = generate()
        self.assertEqual(find_colloquial_markers(text), [])

    def test_generate_uses_hans_word_count_marker(self):
        text = generate()
        self.assertIn("<!-- words-count:zh-Hans -->", text)
        self.assertIn("目前总词条列数", text)
        self.assertNotIn("<!-- words-count:zh-Hant -->", text)

    def test_generate_uses_written_chinese_intro(self):
        text = generate()
        self.assertIn("常见困难一是不知道有哪些字可用", text)
        self.assertNotIn("唔知有咩字", text)


if __name__ == "__main__":
    unittest.main()
