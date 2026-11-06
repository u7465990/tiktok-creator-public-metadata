#!/usr/bin/env bash
# 一条命令完成采集：
#   ./run.sh input/creator_handles_100.csv
# 可选参数透传给 collector，例如：
#   ./run.sh input/creator_handles_100.csv --refresh
#   ./run.sh input/creator_handles_100.csv --limit 5 --no-avatars
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "错误：找不到 python3（需要 Python 3.10+）" >&2
  exit 2
fi

INPUT="${1:-input/creator_handles_100.csv}"
if [ ! -f "$INPUT" ]; then
  echo "错误：输入文件不存在：$INPUT" >&2
  echo "用法：./run.sh input/creator_handles_100.csv" >&2
  exit 2
fi
shift || true

exec python3 -m collector --input "$INPUT" --out . "$@"
