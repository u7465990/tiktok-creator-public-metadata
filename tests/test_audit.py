import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.audit_sample import compare  # noqa: E402


class Facts:
    def __init__(self, nickname, follower_count, signature):
        self.nickname = nickname
        self.follower_count = follower_count
        self.signature = signature


class TestCompare(unittest.TestCase):
    def test_all_same(self):
        record = {"display_name": "TikTok", "follower_count": 1000, "bio": "hi"}
        rows = compare(record, Facts("TikTok", 1000, "hi"))
        self.assertTrue(all(r["verdict"] == "一致" for r in rows))

    def test_follower_growth_within_one_percent_is_minor(self):
        record = {"display_name": "x", "follower_count": 1000, "bio": ""}
        rows = compare(record, Facts("x", 1005, ""))
        verdict = {r["field"]: r["verdict"] for r in rows}
        self.assertEqual(verdict["follower_count"], "轻微变化")

    def test_large_follower_change_is_flagged(self):
        record = {"display_name": "x", "follower_count": 1000, "bio": ""}
        rows = compare(record, Facts("x", 5000, ""))
        verdict = {r["field"]: r["verdict"] for r in rows}
        self.assertEqual(verdict["follower_count"], "变化")

    def test_empty_bio_and_missing_bio_are_equivalent(self):
        record = {"display_name": "x", "follower_count": 1, "bio": None}
        rows = compare(record, Facts("x", 1, ""))
        verdict = {r["field"]: r["verdict"] for r in rows}
        self.assertEqual(verdict["bio"], "一致")

    def test_name_change_is_flagged(self):
        record = {"display_name": "Old", "follower_count": 1, "bio": "b"}
        rows = compare(record, Facts("New", 1, "b"))
        verdict = {r["field"]: r["verdict"] for r in rows}
        self.assertEqual(verdict["display_name"], "变化")


if __name__ == "__main__":
    unittest.main()
