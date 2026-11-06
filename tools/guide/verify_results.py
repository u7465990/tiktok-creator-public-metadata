"""本地校验：结果与输入对齐、Schema 通过、头像文件存在、抽样比对。"""
import csv
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath("."))
from collector.validate import validate_record  # noqa: E402

INPUT = r"creator-public-data-written-test-candidate\input\creator_handles_100.csv"
RESULTS = "results.jsonl"
AVATARS = "avatars"

with open(INPUT, encoding="utf-8-sig", newline="") as fh:
    rows = [r[0].strip() for r in csv.reader(fh) if r and r[0].strip()]
handles = rows[1:]

records = [json.loads(line) for line in open(RESULTS, encoding="utf-8") if line.strip()]

print(f"输入 handle：{len(handles)}")
print(f"结果行数：  {len(records)}")
print(f"是否一一对应：{sorted(handles) == sorted(r['handle'] for r in records)}")
print(f"是否有重复：  {len(records) != len({r['handle'] for r in records})}")

print("\n状态分布：", dict(Counter(r["status"] for r in records)))
print("语言分布：", dict(Counter(r["language"] for r in records)))

problems = []
for r in records:
    problems += [f"{r['handle']}: {e}" for e in validate_record(r)]
print(f"\nSchema/业务校验问题：{len(problems)}")
for p in problems[:10]:
    print("  -", p)

missing_files = [r["handle"] for r in records
                 if r.get("avatar_file") and not os.path.exists(r["avatar_file"])]
print(f"\navatar_file 指向不存在文件：{len(missing_files)}")

files_on_disk = len([f for f in os.listdir(AVATARS)]) if os.path.isdir(AVATARS) else 0
print(f"avatars/ 目录文件数：{files_on_disk}")

ok = [r for r in records if r["status"] == "ok"]
if ok:
    print("\n--- 抽样 3 条 ok ---")
    for r in ok[:3]:
        print(f"{r['handle']:<24} 粉丝={r['follower_count']:<10} "
              f"语言={r['language']}({r['language_confidence']}) "
              f"bio={ (r['bio'] or '')[:40]!r }")

print("\n--- 非 ok 记录 ---")
for r in records:
    if r["status"] != "ok":
        print(f"{r['handle']:<30} {r['status']:<10} {r.get('error')}")

bio_empty = sum(1 for r in records if r["bio"] == "")
print(f"\nbio 为空串（确实没有简介）：{bio_empty}")
print(f"bio 为 null（未采到）：     {sum(1 for r in records if r['bio'] is None)}")
