import unittest

from collector.assemble import build_record
from collector.types import ProfileFacts, Snapshot

URL = "https://www.tiktok.com/@example"


def snapshot(status=200, body="<html></html>", error=None):
    return Snapshot(url=URL, status=status, body=body,
                    fetched_at="2026-11-06T05:00:00Z", error=error)


def facts(**kwargs):
    base = dict(unique_id="example", nickname="Example", signature="hello",
                avatar_url="https://cdn/x.jpg", follower_count=1234,
                private=False)
    base.update(kwargs)
    return ProfileFacts(**base)


class TestBuildRecord(unittest.TestCase):
    def test_ok_keeps_empty_bio_as_empty_string(self):
        rec = build_record("example", "example", snapshot(), "ok", facts(signature=""),
                           None, "en", 0.6, {"method": "x"}, None)
        self.assertEqual(rec["bio"], "")
        self.assertEqual(rec["status"], "ok")
        self.assertIsNone(rec["error"])
        self.assertEqual(rec["source_urls"], [URL])
        self.assertEqual(rec["follower_count"], 1234)

    def test_not_found_nulls_everything(self):
        rec = build_record("ghost", "ghost", snapshot(), "not_found", None,
                           "账号不存在", "und", 0.0, None, None)
        self.assertIsNone(rec["profile_url"])
        self.assertIsNone(rec["display_name"])
        self.assertIsNone(rec["bio"])
        self.assertIsNone(rec["follower_count"])
        self.assertIsNone(rec["avatar_file"])
        self.assertEqual(rec["language"], "und")
        self.assertIsNotNone(rec["error"])

    def test_private_keeps_visible_fields(self):
        rec = build_record("p", "p", snapshot(), "private", facts(private=True, signature="hi"),
                           "account is private", "en", 0.5, None, None)
        self.assertEqual(rec["status"], "private")
        self.assertEqual(rec["bio"], "hi")
        self.assertEqual(rec["follower_count"], 1234)

    def test_error_has_no_source(self):
        rec = build_record("e", "e", snapshot(status=0, body="", error="timeout"),
                           "error", None, "timeout", "und", 0.0, None, None)
        self.assertEqual(rec["source_urls"], [])
        self.assertIsNone(rec["profile_url"])


if __name__ == "__main__":
    unittest.main()
