#!/usr/bin/env python3
"""验收采集结果。

用法（在项目根目录）：
    python3 tools/verify_results.py
    python3 tools/verify_results.py --results results.jsonl --avatars avatars

退出码：0 = 全部通过；1 = 发现问题；2 = 结果文件不存在。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collector.verify import verify  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="input/creator_handles_100.csv")
    ap.add_argument("--results", default="results.jsonl")
    ap.add_argument("--avatars", default="avatars")
    args = ap.parse_args()

    if not os.path.exists(args.results):
        print(f"找不到 {args.results}，先跑 ./run.sh", file=sys.stderr)
        return 2

    result = verify(args.input, args.results, args.avatars)

    print("=" * 52)
    print(f"结果文件 : {args.results}")
    print(f"记录条数 : {result['records']}")
    if result["expected"] is not None:
        print(f"输入条数 : {len(result['expected'])}")
        print(f"一一对应 : {'是' if result['aligned'] else '否  ← 有问题'}")
    else:
        print(f"输入文件不存在，跳过对齐检查：{args.input}")
    duplicates = result["duplicates"]
    print(f"重复记录 : {'无' if not duplicates else str(len(duplicates)) + ' 个  ← 有问题'}")

    print("-" * 52)
    print("状态分布 :", result["status_counts"])
    print("语言分布 :", result["language_counts"])
    print("字段覆盖 :")
    for field, ratio in result["coverage"].items():
        print(f"  {field:<16} {ratio:.0%}")
    print(f"  {'bio 空串':<16} {result['bio_empty']} 条（确实没有简介）")
    if os.path.isdir(args.avatars):
        print(f"头像文件 : {result['avatar_files']} 个")

    print("-" * 52)
    problems = result["problems"]
    if problems:
        print(f"发现 {len(problems)} 个问题：")
        for item in problems[:20]:
            print("  -", item)
        if len(problems) > 20:
            print(f"  ... 另有 {len(problems) - 20} 条")
        return 1

    print("全部通过：字段合法、状态自洽、来源与头像齐备。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
