#!/usr/bin/env bash
# 探测 TikTok oEmbed 接口对三种账号的反应
# 用法：bash ~/probe-oembed.sh
set -u

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

# 1 确定存在 / 1 确定不存在 / 3 个来自输入 CSV（含带点号的）
handles=(
  "tiktok"
  "zzzz_no_such_user_9f3a2b"
  "sr.smits03"
  "boo.licious"
  "spencer_official_2.0"
)

for h in "${handles[@]}"; do
  url="https://www.tiktok.com/oembed?url=https%3A%2F%2Fwww.tiktok.com%2F%40${h}"
  code=$(curl -sS -o /tmp/oembed_probe.json -w '%{http_code}' -A "$UA" "$url" 2>/dev/null)
  size=$(wc -c < /tmp/oembed_probe.json 2>/dev/null | tr -d ' ')
  [ -z "$size" ] && size=0

  echo "=============================================="
  echo "@${h}   →   HTTP ${code}   ${size} 字节"

  if [ "$code" = "200" ]; then
    echo "  author_name : $(grep -o '"author_name":"[^"]*"' /tmp/oembed_probe.json | head -1)"
    echo "  author_url  : $(grep -o '"author_url":"[^"]*"' /tmp/oembed_probe.json | head -1)"
    echo "  thumbnail   : $(grep -o '"thumbnail_url":"[^"]*"' /tmp/oembed_probe.json | head -1 | cut -c1-140)"
    echo "  title       : $(grep -o '"title":"[^"]*"' /tmp/oembed_probe.json | head -1 | cut -c1-120)"
  else
    echo "  原始返回 : $(head -c 300 /tmp/oembed_probe.json 2>/dev/null)"
  fi
  echo
  sleep 2
done

echo "=============================================="
echo "探测结束"
