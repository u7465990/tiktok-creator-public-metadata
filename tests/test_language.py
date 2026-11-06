import unittest

from collector.language import detect_language


class TestDetectLanguage(unittest.TestCase):
    def test_empty_is_und_with_zero_confidence(self):
        self.assertEqual(detect_language(None)[0], "und")
        self.assertEqual(detect_language("")[0], "und")
        self.assertEqual(detect_language("")[1], 0.0)

    def test_script_detection(self):
        self.assertEqual(detect_language("热爱生活，记录每一天")[0], "zh")
        self.assertEqual(detect_language("毎日を楽しく過ごす")[0], "ja")
        self.assertEqual(detect_language("Привет, мир")[0], "ru")

    def test_latin_stopwords(self):
        self.assertEqual(detect_language("Your next discovery is waiting on TikTok")[0], "en")
        self.assertEqual(detect_language("Mi vida y mi amor")[0], "es")

    def test_strong_marker_allows_single_hit(self):
        # 只命中 "the"，但文本够长且该词几乎只出现在英语里
        for text in ("Living the American Dream",
                     "All the fun things!!",
                     "Year 2 of the Summer League"):
            code, confidence, evidence = detect_language(text)
            self.assertEqual(code, "en", text)
            self.assertEqual(evidence["method"], "strong-marker")
            self.assertLessEqual(confidence, 0.5)

    def test_strong_marker_needs_enough_tokens(self):
        self.assertEqual(detect_language("the")[0], "und")
        self.assertEqual(detect_language("my")[0], "und")

    def test_strong_marker_does_not_hijack_spanish(self):
        # 西语里没有 the/and/my 这类词，不应被强标记词规则吃掉
        self.assertEqual(detect_language("Mi vida y mi amor")[0], "es")

    def test_insufficient_evidence_stays_und(self):
        code, confidence, evidence = detect_language("hi")
        self.assertEqual(code, "und")
        self.assertLess(confidence, 0.5)
        self.assertIsNotNone(evidence)

    def test_confidence_bounds(self):
        for text in ("热爱生活", "Your life is your story", "abc"):
            _, confidence, _ = detect_language(text)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
