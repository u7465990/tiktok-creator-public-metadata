#!/usr/bin/env bash
# 一键清理采集产物，方便重跑或用新输入做扩展。
#
#   ./clean.sh          删除结果与头像，保留 cache/（重跑约 1 分钟）
#   ./clean.sh --all    连 cache/ 一起删（彻底重来，约 6 分钟）
#   ./clean.sh -n       只打印将要删除的内容，不真删
#   ./clean.sh -y       跳过确认
set -euo pipefail
cd "$(dirname "$0")"

YES=0
WITH_CACHE=0
DRY=0

for arg in "$@"; do
  case "$arg" in
    --all|--cache) WITH_CACHE=1 ;;
    -y|--yes)      YES=1 ;;
    -n|--dry-run)  DRY=1 ;;
    -h|--help)     sed -n '2,9p' "$0"; exit 0 ;;
    *)             echo "未知参数：$arg（用 --help 查看用法）" >&2; exit 2 ;;
  esac
done

targets=(results.jsonl report.json avatars out_test)
if [ "$WITH_CACHE" = 1 ]; then
  targets+=(cache)
fi

echo "将清理："
found=0
for t in "${targets[@]}"; do
  if [ -e "$t" ]; then
    size=$(du -sh "$t" 2>/dev/null | cut -f1)
    echo "  - $t  ($size)"
    found=$((found + 1))
  fi
done

pycache_count=$(find . -type d -name __pycache__ -not -path './.git/*' | wc -l | tr -d ' ')
if [ "$pycache_count" -gt 0 ]; then
  echo "  - __pycache__ 目录 ${pycache_count} 个"
fi

if [ "$found" -eq 0 ] && [ "$pycache_count" -eq 0 ]; then
  echo "没有需要清理的内容。"
  exit 0
fi

if [ "$DRY" = 1 ]; then
  echo
  echo "（--dry-run：以上内容未被删除）"
  exit 0
fi

if [ "$YES" != 1 ]; then
  echo
  printf '确认删除？[y/N] '
  read -r answer || answer=""
  case "$answer" in
    y|Y|yes|YES) ;;
    *) echo "已取消。"; exit 1 ;;
  esac
fi

for t in "${targets[@]}"; do
  if [ -e "$t" ]; then
    rm -rf "$t"
  fi
done

find . -type d -name __pycache__ -not -path './.git/*' -exec rm -rf {} + 2>/dev/null || true

echo
echo "清理完成。"
if [ "$WITH_CACHE" = 1 ]; then
  echo "缓存已清空：下次运行会重新抓取全部页面（约 6 分钟）。"
else
  echo "缓存已保留：下次运行会复用已抓页面（约 1 分钟）。"
  echo "如需彻底重来，用 ./clean.sh --all"
fi
