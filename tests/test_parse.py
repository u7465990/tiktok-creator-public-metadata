import os
import unittest

from collector.assemble import interpret, normalize_handle
from collector.parse import looks_like_waf, parse_profile

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")


def fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8", errors="ignore") as fh:
        return fh.read()


class TestNormalize(unittest.TestCase):
    def test_variants(self):
        self.assertEqual(normalize_handle("  @SR.smits03 "), "sr.smits03")
        self.assertEqual(normalize_handle("https://www.tiktok.com/@boo.licious?lang=en"), "boo.licious")
        self.assertEqual(normalize_handle("tiktok.com/@abc/"), "abc")
        self.assertEqual(normalize_handle("Spencer_Official_2.0"), "spencer_official_2.0")


class TestParseOk(unittest.TestCase):
    def setUp(self):
        self.html = fixture("profile_ok.html")

    def test_fields(self):
        facts = parse_profile(self.html)
        self.assertEqual(facts.nickname, "TikTok")
        self.assertEqual(facts.unique_id, "tiktok")
        self.assertEqual(facts.follower_count, 96600000)
        self.assertIsInstance(facts.follower_count, int)
        self.assertTrue(facts.avatar_url.startswith("https://"))
        self.assertFalse(facts.private)
        self.assertIsInstance(facts.signature, str)

    def test_interpret_ok(self):
        status, facts, error = interpret(self.html)
        self.assertEqual(status, "ok")
        self.assertIsNotNone(facts)
        self.assertIsNone(error)


class TestParseMissing(unittest.TestCase):
    def test_not_found(self):
        status, facts, error = interpret(fixture("profile_missing.html"))
        self.assertEqual(status, "not_found")
        self.assertIsNone(facts)
        self.assertIn("statusCode=10221", error)


class TestWaf(unittest.TestCase):
    def test_small_challenge_page_is_blocked(self):
        html = ('<html><body>Please wait...'
                '<p id="wci" class="_wafchallengeid"></p></body></html>')
        self.assertTrue(looks_like_waf(html))
        status, facts, error = interpret(html)
        self.assertEqual(status, "blocked")
        self.assertIsNone(facts)
        self.assertIn("waf_challenge", error)


class TestPrivate(unittest.TestCase):
    def test_private_carries_reason(self):
        html = (
            '<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">'
            '{"__DEFAULT_SCOPE__":{"webapp.user-detail":{"statusCode":0,"userInfo":{'
            '"user":{"uniqueId":"locked","nickname":"Locked","privateAccount":true,'
            '"signature":"hi"},"stats":{"followerCount":42}}}}}'
            '</script>'
        )
        status, facts, error = interpret(html)
        self.assertEqual(status, "private")
        self.assertIsNotNone(facts)
        self.assertIsNotNone(error)
        self.assertIn("私密", error)


if __name__ == "__main__":
    unittest.main()
