"""结果校验：Schema 要求 + 业务一致性断言。只检查，不修复。"""
import re

from .types import STATUSES

_LANG_RE = re.compile(r"^([a-z]{2}|und)$")

REQUIRED = [
    "handle", "normalized_handle", "profile_url", "display_name", "avatar_url",
    "avatar_file", "bio", "follower_count", "language", "language_confidence",
    "language_evidence", "source_urls", "collected_at", "status", "error",
]


def validate_record(rec: dict) -> list:
    errors = []

    for key in REQUIRED:
        if key not in rec:
            errors.append(f"缺失字段 {key}")
    if errors:
        return errors

    if not isinstance(rec["handle"], str) or not rec["handle"].strip():
        errors.append("handle 必须是非空字符串")
    if not isinstance(rec["normalized_handle"], str) or not rec["normalized_handle"].strip():
        errors.append("normalized_handle 必须是非空字符串")

    if rec["follower_count"] is not None:
        if not isinstance(rec["follower_count"], int) or isinstance(rec["follower_count"], bool):
            errors.append("follower_count 必须是整数或 null")
        elif rec["follower_count"] < 0:
            errors.append("follower_count 不能为负")

    if not isinstance(rec["language"], str) or not _LANG_RE.match(rec["language"]):
        errors.append("language 必须是两位小写 ISO 639-1 或 und")

    conf = rec["language_confidence"]
    if not isinstance(conf, (int, float)) or isinstance(conf, bool):
        errors.append("language_confidence 必须是数字")
    elif not (0 <= conf <= 1):
        errors.append("language_confidence 必须在 [0,1]")

    if rec["status"] not in STATUSES:
        errors.append(f"status 非法：{rec['status']}")

    if not isinstance(rec["source_urls"], list):
        errors.append("source_urls 必须是数组")
    elif len(set(rec["source_urls"])) != len(rec["source_urls"]):
        errors.append("source_urls 有重复")

    # 业务一致性（对应 ADR-0002/0003/0004/0006）
    if rec["status"] == "ok":
        if not rec["source_urls"]:
            errors.append("status=ok 必须至少有一个来源 URL")
        if rec["bio"] is None:
            errors.append("status=ok 时 bio 不应为 null（空简介用空串）")
        if rec["error"] is not None:
            errors.append("status=ok 时 error 必须为 null")
    else:
        if rec["bio"] is not None and rec["status"] != "private":
            errors.append("非 ok/private 状态下 bio 必须为 null")
        if rec["error"] is None:
            errors.append(f"status={rec['status']} 必须写明 error 原因")

    return errors


def validate_all(records: list) -> list:
    problems = []
    seen = set()
    for rec in records:
        for err in validate_record(rec):
            problems.append(f"{rec.get('handle', '?')}: {err}")
        h = rec.get("handle")
        if h in seen:
            problems.append(f"{h}: handle 重复")
        seen.add(h)
    return problems
