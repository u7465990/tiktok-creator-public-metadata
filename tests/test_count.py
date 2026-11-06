import unittest

from collector.count import parse_count


class TestParseCount(unittest.TestCase):
    def test_abbreviated(self):
        self.assertEqual(parse_count("1.2K"), 1200)
        self.assertEqual(parse_count("3.4M"), 3400000)
        self.assertEqual(parse_count("12.3K"), 12300)
        self.assertEqual(parse_count("1.2B"), 1200000000)

    def test_separators_and_cn(self):
        self.assertEqual(parse_count("12,345"), 12345)
        self.assertEqual(parse_count("1.2万"), 12000)
        self.assertEqual(parse_count("3亿"), 300000000)
        self.assertEqual(parse_count("1,234 粉丝"), 1234)

    def test_unknown_is_none_not_zero(self):
        for text in ("", "   ", "—", "N/A", "null", "abc", "-5"):
            self.assertIsNone(parse_count(text), text)

    def test_already_int(self):
        self.assertEqual(parse_count(0), 0)
        self.assertEqual(parse_count(42), 42)
        self.assertIsNone(parse_count(-1))


if __name__ == "__main__":
    unittest.main()
