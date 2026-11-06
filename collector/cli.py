"""命令行入口：读 CSV -> 逐条采集 -> results.jsonl / avatars / report.json。"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

from .assemble import build_record, decide_status, normalize_handle, profile_url_for
from .avatars import download_avatar, slugify
from .fetch import Fetcher
from .language import detect_language
from .report import build_report
from .validate import validate_all


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_handles(path: str) -> list:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        rows = [row for row in reader if row and row[0].strip()]
    if not rows:
        return []
    if rows[0][0].strip().lower() in ("handle", "handles", "username"):
        rows = rows[1:]
    return [row[0].strip() for row in rows]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="collector", description="TikTok 公开元信息采集")
    p.add_argument("--input", required=True, help="输入 CSV（首列 handle）")
    p.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    p.add_argument("--limit", type=int, default=0, help="只跑前 N 条（调试用）")
    p.add_argument("--delay", type=float, default=3.0, help="请求间隔秒数（含抖动）")
    p.add_argument("--refresh", action="store_true", help="忽略快照缓存，重新抓取")
    p.add_argument("--no-avatars", action="store_true", help="不下载头像")
    return p


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    args = build_parser().parse_args(argv)
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    avatar_dir = os.path.join(out_dir, "avatars")
    cache_dir = os.path.join(out_dir, "cache")
    results_path = os.path.join(out_dir, "results.jsonl")
    report_path = os.path.join(out_dir, "report.json")

    handles = read_handles(args.input)
    if args.limit and args.limit > 0:
        handles = handles[: args.limit]
    if not handles:
        print("输入为空", file=sys.stderr)
        return 2

    fetcher = Fetcher(cache_dir, delay=args.delay, refresh=args.refresh)
    started_at = _now()
    started = datetime.now(timezone.utc)
    records = []

    print(f"开始采集：{len(handles)} 条，间隔约 {args.delay}s，输出到 {out_dir}")
    for index, raw in enumerate(handles, start=1):
        normalized = normalize_handle(raw)
        url = profile_url_for(normalized)

        snapshot = fetcher.get(url)
        status, facts, error = decide_status(snapshot)

        avatar_file = None
        if facts and facts.avatar_url and not args.no_avatars:
            avatar_file, reason = download_avatar(facts.avatar_url, avatar_dir, slugify(normalized))
            if reason:
                error = f"{error}；头像下载失败：{reason}" if error else f"头像下载失败：{reason}"

        bio_text = facts.signature if facts else None
        language, confidence, evidence = detect_language(bio_text)

        record = build_record(
            handle=raw,
            normalized=normalized,
            snapshot=snapshot,
            status=status,
            facts=facts,
            error=error,
            language=language,
            confidence=confidence,
            evidence=evidence,
            avatar_file=avatar_file,
        )
        records.append(record)

        flag = "缓存" if snapshot.from_cache else "抓取"
        print(f"[{index}/{len(handles)}] {raw:<32} {status:<10} {flag}")

    with open(results_path, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    finished_at = _now()
    duration = (datetime.now(timezone.utc) - started).total_seconds()
    report = build_report(
        input_count=len(records),
        records=records,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration,
        environment={
            "user_agent": "iPhone Safari（桌面 UA 会被 WAF 拦）",
            "delay_seconds": args.delay,
            "limit": args.limit or len(handles),
            "python": sys.version.split()[0],
        },
    )
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    problems = validate_all(records)
    print("\n状态分布：", report["status_counts"])
    print("字段覆盖：", report["field_coverage"])
    print(f"产物：{results_path}")
    print(f"      {report_path}")
    if problems:
        print(f"\n校验发现 {len(problems)} 个问题：", file=sys.stderr)
        for item in problems[:20]:
            print("  - " + item, file=sys.stderr)
        return 1
    print("\n校验通过：所有记录符合 Schema 与业务断言。")
    return 0
