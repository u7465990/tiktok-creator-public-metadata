"""report.json 聚合。纯函数。"""
from collections import Counter
from typing import Optional
from urllib.parse import urlparse


def _coverage(records: list, field: str) -> float:
    if not records:
        return 0.0
    hit = sum(1 for r in records if r.get(field) not in (None, "", [], {}))
    return round(hit / len(records), 4)


def build_report(input_count: int, records: list, started_at: str, finished_at: str,
                 duration_seconds: float, environment: Optional[dict] = None) -> dict:
    status_counts = Counter(r.get("status") for r in records)
    hosts = Counter()
    for r in records:
        for url in r.get("source_urls") or []:
            host = urlparse(url).netloc or "unknown"
            hosts[host] += 1

    languages = Counter(r.get("language") for r in records)
    total = len(records)
    non_und = sum(1 for r in records if r.get("language") not in (None, "und"))

    return {
        "input_count": input_count,
        "result_count": len(records),
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": round(duration_seconds, 2),
        "status_counts": {
            "ok": status_counts.get("ok", 0),
            "not_found": status_counts.get("not_found", 0),
            "private": status_counts.get("private", 0),
            "blocked": status_counts.get("blocked", 0),
            "error": status_counts.get("error", 0),
        },
        "field_coverage": {
            "profile_url": _coverage(records, "profile_url"),
            "display_name": _coverage(records, "display_name"),
            "avatar_url": _coverage(records, "avatar_url"),
            "avatar_file": _coverage(records, "avatar_file"),
            "bio": _coverage(records, "bio"),
            "follower_count": _coverage(records, "follower_count"),
            "language": round(non_und / total, 4) if total else 0.0,
        },
        "language_distribution": dict(languages.most_common()),
        "source_distribution": dict(hosts.most_common()),
        "environment": environment or {},
        "notes": "bio 覆盖按非 null 计（空串算已观测）；avatar_url 含时效签名，过期属正常。",
    }
