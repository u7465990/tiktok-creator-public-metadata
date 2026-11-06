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
