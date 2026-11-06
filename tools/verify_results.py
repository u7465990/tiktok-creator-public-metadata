#!/usr/bin/env python3
"""验收采集结果：与输入对齐、字段合法性、业务断言、头像文件、统计。

用法（在项目根目录）：
    python3 tools/verify_results.py
    python3 tools/verify_results.py --results results.jsonl --avatars avatars

退出码：0 = 全部通过；1 = 发现问题。
"""
import argparse
import collections
import csv
import json
import os
import re
import sys

STATUSES = {"ok", "not_found", "private", "blocked", "error"}
REQUIRED = [
    "handle", "normalized_handle", "profile_url", "display_name", "avatar_url",
    "avatar_file", "bio", "follower_count", "language", "language_confidence",
    "language_evidence", "source_urls", "collected_at", "status", "error",
]
LANG_RE = re.compile(r"^([a-z]{2}|und)$")


def read_handles(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r[0].strip() for r in csv.reader(fh) if r and r[0].strip()]
    return rows[1:] if rows and rows[0].lower() in ("handle", "handles", "username") else rows


def load_records(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def check_record(rec, avatar_dir):
    """返回这条记录的问题列表。"""
    problems = []
    name = rec.get("handle", "?")

    for key in REQUIRED:
        if key not in rec:
            problems.append(f"{name}: 缺字段 {key}")
    if any(f"缺字段" in p for p in problems):
        return problems

    if not isinstance(rec["handle"], str) or not rec["handle"].strip():
        problems.append(f"{name}: handle 为空")
    if not isinstance(rec["normalized_handle"], str) or not rec["normalized_handle"]:
        problems.append(f"{name}: normalized_handle 为空")

    fc = rec["follower_count"]
    if fc is not None and (not isinstance(fc, int) or isinstance(fc, bool) or fc < 0):
        problems.append(f"{name}: follower_count 必须是非负整数或 null，实际 {fc!r}")

    if not isinstance(rec["language"], str) or not LANG_RE.match(rec["language"]):
        problems.append(f"{name}: language 非法 {rec['language']!r}")

    conf = rec["language_confidence"]
    if not isinstance(conf, (int, float)) or isinstance(conf, bool) or not 0 <= conf <= 1:
        problems.append(f"{name}: language_confidence 越界 {conf!r}")

    if rec["status"] not in STATUSES:
        problems.append(f"{name}: status 非法 {rec['status']!r}")

    urls = rec["source_urls"]
    if not isinstance(urls, list) or any(not isinstance(u, str) for u in urls):
        problems.append(f"{name}: source_urls 必须是字符串数组")
    elif len(urls) != len(set(urls)):
        problems.append(f"{name}: source_urls 有重复")

    status = rec["status"]
    if status == "ok":
        if not urls:
            problems.append(f"{name}: status=ok 但没有来源 URL")
        if rec["bio"] is None:
            problems.append(f"{name}: status=ok 时 bio 不应为 null（空简介应为空串）")
        if rec["error"] is not None:
            problems.append(f"{name}: status=ok 时 error 必须为 null")
    else:
        if rec["bio"] is not None and status != "private":
            problems.append(f"{name}: {status} 状态下 bio 应为 null")
        if rec["error"] is None:
            problems.append(f"{name}: {status} 必须写明 error 原因")

    avatar = rec.get("avatar_file")
    if avatar:
        if os.path.isabs(avatar):
            problems.append(f"{name}: avatar_file 必须是相对路径")
        elif not os.path.exists(os.path.join(avatar_dir, os.path.basename(avatar))):
            problems.append(f"{name}: avatar_file 指向的文件不存在 {avatar}")

    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="input/creator_handles_100.csv")
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--avatars", default="avatars")
    args = ap.parse_args()

    if not os.path.exists(args.results):
        print(f"找不到 {args.results}，先跑 ./run.sh", file=sys.stderr)
        return 2

    records = load_records(args.results)
    problems = []
    handles = [r.get("handle", "") for r in records]

    print("=" * 52)
    print(f"结果文件 : {args.results}")
    print(f"记录条数 : {len(records)}")

    if os.path.exists(args.input):
        expected = read_handles(args.input)
        print(f"输入条数 : {len(expected)}")
        same = sorted(expected) == sorted(handles)
        print(f"一一对应 : {'是' if same else '否  ← 有问题'}")
        if not same:
            missing = set(expected) - set(handles)
            extra = set(handles) - set(expected)
            if missing:
                problems.append(f"缺少 {len(missing)} 个 handle，例如 {sorted(missing)[:5]}")
            if extra:
                problems.append(f"多出 {len(extra)} 个 handle，例如 {sorted(extra)[:5]}")
    else:
        print(f"输入文件不存在，跳过对齐检查：{args.input}")

    dup = [h for h, c in collections.Counter(handles).items() if c > 1]
    print(f"重复记录 : {'无' if not dup else f'{len(dup)} 个 ← 有问题'}")
    if dup:
        problems.append(f"重复 handle：{sorted(dup)[:5]}")

    for rec in records:
        problems.extend(check_record(rec, args.avatars))

    status_counts = collections.Counter(r.get("status") for r in records)
    langs = collections.Counter(r.get("language") for r in records)
    total = len(records) or 1
    non_null = lambda field: sum(1 for r in records if r.get(field) not in (None, "", [], {}))  # noqa: E731

    print("-" * 52)
    print("状态分布 :", dict(status_counts))
    print("语言分布 :", dict(langs))
    print("字段覆盖 :")
    for field in ("profile_url", "display_name", "avatar_url", "avatar_file",
                  "bio", "follower_count"):
        print(f"  {field:<16} {non_null(field) / total:.0%}")
    print(f"  {'bio 空串':<16} {sum(1 for r in records if r.get('bio') == '')} 条（确实没有简介）")

    if os.path.isdir(args.avatars):
        print(f"头像文件 : {len(os.listdir(args.avatars))} 个")

    print("-" * 52)
    if problems:
        print(f"发现 {len(problems)} 个问题：")
        for p in problems[:20]:
            print("  -", p)
        if len(problems) > 20:
            print(f"  ... 另有 {len(problems) - 20} 条")
        return 1
    print("全部通过：字段合法、状态自洽、来源与头像齐备。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
