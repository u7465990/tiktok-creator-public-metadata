"""端到端测试：用真实页面夹具跑完整流程，全程不联网。"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import unittest
import uuid
from unittest import mock

from collector.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "profile_ok.html")
URL = "https://www.tiktok.com/@tiktok"


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        # 建在当前目录下（沙箱与 CI 都可写）；不用 tempfile.mkdtemp，
        # 它在部分 Windows 沙箱下会生成不可写的目录。
        self.tmp = os.path.join(os.getcwd(), ".e2e-" + uuid.uuid4().hex[:8])
        os.makedirs(self.tmp, exist_ok=True)
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        self.input = os.path.join(self.tmp, "in.csv")
        with open(self.input, "w", encoding="utf-8") as fh:
            fh.write("handle\ntiktok\n")

        self.out = os.path.join(self.tmp, "out")
        cache = os.path.join(self.out, "cache")
        os.makedirs(cache)

        # 把真实页面按线上缓存的命名规则塞进去
        key = hashlib.sha1(URL.encode("utf-8")).hexdigest()
        shutil.copy(FIXTURE, os.path.join(cache, key + ".html"))
        with open(os.path.join(cache, key + ".json"), "w", encoding="utf-8") as fh:
            json.dump({"url": URL, "status": 200,
                       "fetched_at": "2026-11-06T00:00:00Z", "error": None}, fh)

    def run_cli(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["--input", self.input, "--out", self.out, "--no-avatars"])
        return code, buffer.getvalue()

    def test_writes_one_valid_record(self):
        code, _ = self.run_cli()
        self.assertEqual(code, 0, "校验应当通过")

        path = os.path.join(self.out, "results.jsonl")
        lines = [line for line in open(path, encoding="utf-8").read().splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)

        record = json.loads(lines[0])
        self.assertEqual(record["handle"], "tiktok")
        self.assertEqual(record["status"], "ok")
        self.assertEqual(record["display_name"], "TikTok")
        self.assertEqual(record["follower_count"], 96600000)
        self.assertEqual(record["source_urls"], [URL])
        self.assertIsNone(record["error"])

        self.assertTrue(os.path.exists(os.path.join(self.out, "report.json")))

    def test_second_run_reuses_cache_without_network(self):
        self.run_cli()
        with mock.patch("collector.fetch.Fetcher._request",
                        side_effect=AssertionError("不应该再访问网络")):
            code, output = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("缓存", output)


if __name__ == "__main__":
    unittest.main()
