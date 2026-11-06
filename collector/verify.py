"""结果验收：输入对齐、字段合法性、业务断言、头像文件、统计。"""
import collections
import csv
import json
import os

from .validate import validate_record


def read_handles(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r[0].strip() for r in csv.reader(fh) if r and r[0].strip()]
    return rows[1:] if rows and rows[0].lower() in ("handle", "handles", "username") else rows


def load_records(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def check_avatar(record, avatar_dir):
    """头像字段必须是相对路径，且文件真实存在。"""
    avatar = record.get("avatar_file")
    if not avatar:
        return []
    if os.path.isabs(avatar):
        return [f"{record.get('handle', '?')}: avatar_file 必须是相对路径"]
    if not os.path.exists(os.path.join(avatar_dir, os.path.basename(avatar))):
        return [f"{record.get('handle', '?')}: avatar_file 指向的文件不存在 {avatar}"]
    return []


def verify(input_path=None, results_path="results.jsonl", avatars_dir="avatars"):
    """返回统计与问题清单；problems 为空即通过。"""
    records = load_records(results_path)
    handles = [r.get("handle", "") for r in records]
    problems = []

    expected = None
    aligned = None
    if input_path and os.path.exists(input_path):
        expected = read_handles(input_path)
        aligned = sorted(expected) == sorted(handles)
        if not aligned:
            missing = set(expected) - set(handles)
            extra = set(handles) - set(expected)
            if missing:
                problems.append(f"缺少 {len(missing)} 个 handle，例如 {sorted(missing)[:5]}")
            if extra:
                problems.append(f"多出 {len(extra)} 个 handle，例如 {sorted(extra)[:5]}")

    duplicates = [h for h, count in collections.Counter(handles).items() if count > 1]
    if duplicates:
        problems.append(f"重复 handle：{sorted(duplicates)[:5]}")

    for record in records:
        problems.extend(validate_record(record))
        problems.extend(check_avatar(record, avatars_dir))

    total = len(records) or 1
    coverage = {}
    for field in ("profile_url", "display_name", "avatar_url", "avatar_file",
                  "bio", "follower_count"):
        coverage[field] = sum(1 for r in records if r.get(field) not in (None, "", [], {})) / total

    avatar_files = len(os.listdir(avatars_dir)) if os.path.isdir(avatars_dir) else 0

    return {
        "records": len(records),
        "expected": expected,
        "aligned": aligned,
        "duplicates": duplicates,
        "problems": problems,
        "status_counts": dict(collections.Counter(r.get("status") for r in records)),
        "language_counts": dict(collections.Counter(r.get("language") for r in records)),
        "coverage": coverage,
        "bio_empty": sum(1 for r in records if r.get("bio") == ""),
        "avatar_files": avatar_files,
    }
