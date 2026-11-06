#!/usr/bin/env python3
"""抽样复核：随机抽 N 条 ok 记录，重新抓取公开主页并逐字段比对。

用法（在能访问 TikTok 的机器上）：
    python3 tools/audit_sample.py --sample 20
    python3 tools/audit_sample.py --sample 20 --seed 42 --delay 3

产物：audit.md + audit.json
退出码：0 = 全部复核成功；1 = 有账号在复核时已不可访问。
"""
import argparse
import json
import os
import random
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.assemble import decide_status, profile_url_for  # noqa: E402
from collector.fetch import Fetcher  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compare(record: dict, facts) -> list:
    """逐字段比对，返回 [{field, before, after, verdict}]。"""
    rows = []

    before = record.get("display_name")
    after = facts.nickname
    rows.append({"field": "display_name", "before": before, "after": after,
                 "verdict": "一致" if before == after else "变化"})

    before = record.get("follower_count")
    after = facts.follower_count
    if before == after:
        verdict = "一致"
    elif before and after and abs(after - before) / max(before, 1) <= 0.01:
        verdict = "轻微变化"          # 粉丝数会自然增长，1% 内视为正常
    else:
        verdict = "变化"
    rows.append({"field": "follower_count", "before": before, "after": after,
                 "verdict": verdict})

    before = record.get("bio")
    after = facts.signature
    same = (before or "") == (after or "")
    rows.append({"field": "bio", "before": before, "after": after,
                 "verdict": "一致" if same else "变化"})

    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--delay", type=float, default=3.0)
    ap.add_argument("--cache", default=".audit-cache")
    ap.add_argument("--out", default="audit.md")
    args = ap.parse_args()

    with open(args.results, encoding="utf-8") as fh:
        records = [json.loads(line) for line in fh if line.strip()]

    pool = [r for r in records if r.get("status") == "ok"]
    random.Random(args.seed).shuffle(pool)
    sample = pool[: args.sample]
    if not sample:
        print("没有可复核的 ok 记录", file=sys.stderr)
        return 2

    print(f"从 {len(pool)} 条 ok 记录中抽取 {len(sample)} 条（seed={args.seed}）")
    fetcher = Fetcher(args.cache, delay=args.delay, refresh=True)

    checked_at = now()
    details = []
    failures = []

    for index, record in enumerate(sample, start=1):
        url = record.get("profile_url") or profile_url_for(record["normalized_handle"])
        snapshot = fetcher.get(url)
        status, facts, error = decide_status(snapshot)
        entry = {"handle": record["handle"], "url": url, "status": status}

        if status != "ok" or facts is None:
            entry["error"] = error
            details.append(entry)
            failures.append(entry)
            print(f"[{index}/{len(sample)}] {record['handle']:<28} 复核失败：{status}")
            continue

        rows = compare(record, facts)
        entry["rows"] = rows
        entry["avatar_file"] = record.get("avatar_file")
        entry["avatar_exists"] = bool(record.get("avatar_file")) and os.path.exists(record["avatar_file"])
        details.append(entry)

        changed = [r["field"] for r in rows if r["verdict"] not in ("一致", "轻微变化")]
        print(f"[{index}/{len(sample)}] {record['handle']:<28} "
              + ("一致" if not changed else "变化：" + ",".join(changed)))

    consistent = sum(1 for d in details if "rows" in d
                     and all(r["verdict"] in ("一致", "轻微变化") for r in d["rows"]))
    lines = [
        "# 抽样复核报告",
        "",
        f"- 样本数量：{len(sample)} / {len(pool)} 条 ok 记录（随机种子 {args.seed}）",
        f"- 复核时间：{checked_at}",
        f"- 复核方式：重新请求 `profile_url`，解析 `__UNIVERSAL_DATA_FOR_REHYDRATION__` 后与结果文件逐字段比对",
        f"- 一致（含粉丝数 1% 内自然变化）：{consistent} / {len(sample)}",
        "",
        "| # | handle | display_name | follower_count | bio | 结论 |",
        "|---|---|---|---|---|---|",
    ]

    for index, entry in enumerate(details, start=1):
        if "rows" not in entry:
            lines.append(f"| {index} | `{entry['handle']}` | — | — | — | 复核失败（{entry['status']}） |")
            continue
        by_field = {r["field"]: r for r in entry["rows"]}
        verdicts = {r["field"]: r["verdict"] for r in entry["rows"]}
        ok = all(v in ("一致", "轻微变化") for v in verdicts.values())
        lines.append(
            f"| {index} | `{entry['handle']}` "
            f"| {by_field['display_name']['after'] or '—'}（{verdicts['display_name']}） "
            f"| {by_field['follower_count']['after']}（{verdicts['follower_count']}） "
            f"| {(by_field['bio']['after'] or '（空）')[:24]}（{verdicts['bio']}） "
            f"| {'✅ 一致' if ok else '⚠️ 有变化'} |"
        )

    lines += [
        "",
        "> 粉丝数在两次抓取之间会自然增长，1% 以内记为“轻微变化”，不视为不一致。",
        "> 复核时已不可访问的账号（私密/删除/限流）单独列出，不参与一致率计算。",
    ]

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(args.out.replace(".md", ".json"), "w", encoding="utf-8") as fh:
        json.dump({"checked_at": checked_at, "sample": len(sample),
                   "consistent": consistent, "details": details},
                  fh, ensure_ascii=False, indent=2)

    print(f"\n一致：{consistent}/{len(sample)}；复核失败：{len(failures)}")
    print(f"报告：{args.out}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
