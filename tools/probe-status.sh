#!/usr/bin/env bash
# 用 iPhone UA 探测 4 个账号，确认 not_found / ok 的真实信号
# 用法：bash ~/probe-status.sh
set -u

UA='Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'
OUT="$HOME/probe-status"
mkdir -p "$OUT"

handles=(
  "tiktok"
  "zzzz_no_such_user_9f3a2b"
  "sr.smits03"
  "boo.licious"
)

for h in "${handles[@]}"; do
  body="$OUT/${h}.html"
  code=$(curl -sS -L --compressed --max-time 30 \
    -A "$UA" \
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
    -H 'Accept-Language: en-US,en;q=0.9' \
    -H 'Referer: https://www.tiktok.com/' \
    -o "$body" -w '%{http_code}' \
    "https://www.tiktok.com/@${h}" 2>/dev/null)

  size=$(wc -c < "$body" 2>/dev/null | tr -d ' '); [ -z "$size" ] && size=0

  echo "=================================================="
  echo "@${h}   HTTP ${code}   ${size} 字节"

  if [ "$size" -lt 3000 ]; then
    echo "  （页面太小，可能是错误页：$(head -c 160 "$body" | tr -d '\n')）"
    continue
  fi

  echo "  statusCode  : $(grep -o '"statusCode":[-0-9]*' "$body" | head -1)"
  echo "  statusMsg   : $(grep -o '"statusMsg":"[^"]*"' "$body" | head -1)"
  echo "  uniqueId    : $(grep -o '"uniqueId":"[^"]*"' "$body" | head -1)"
  echo "  nickname    : $(grep -o '"nickname":"[^"]*"' "$body" | head -1)"
  echo "  followerCnt : $(grep -o '"followerCount":[0-9]*' "$body" | head -1)"
  echo "  privateAcct : $(grep -o '"privateAccount":[a-z]*' "$body" | head -1)"
  echo "  有 signature: $(grep -c '"signature"' "$body")"
  echo "  有 itemList : $(grep -c '"itemList"' "$body")"
  sleep 3
done

echo "=================================================="
echo "页面已保存到：${OUT}"
