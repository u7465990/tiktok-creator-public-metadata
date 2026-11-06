#!/usr/bin/env bash
# 用四种"长相"请求同一个 TikTok 主页，看 WAF 是否放行
# 用法：bash ~/probe-html.sh [handle]     默认 handle = tiktok
set -u

HANDLE="${1:-tiktok}"
OUT="$HOME/probe-html"
mkdir -p "$OUT"

DESK='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
IPH='Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1'

NAMES=(); CODES=(); SIZES=(); UNIS=(); WAFS=(); FOLS=()

summarize() {
  local name="$1" body="$2" code="$3"
  local size uni waf fol
  size=$(wc -c < "$body" 2>/dev/null | tr -d ' '); [ -z "$size" ] && size=0
  uni=$(grep -c '__UNIVERSAL_DATA_FOR_REHYDRATION__' "$body" 2>/dev/null || true)
  waf=$(grep -c -E 'Please wait|_wafchallengeid' "$body" 2>/dev/null || true)
  fol=$(grep -o 'followerCount[^,}]*' "$body" 2>/dev/null | head -1)
  [ -z "$uni" ] && uni=0
  [ -z "$waf" ] && waf=0
  NAMES+=("$name"); CODES+=("$code"); SIZES+=("$size"); UNIS+=("$uni"); WAFS+=("$waf"); FOLS+=("${fol:-none}")
  printf '[%-12s] HTTP %-3s %7sB  universal=%s  waf=%s  %s\n' \
    "$name" "$code" "$size" "$uni" "$waf" "${fol:-}"
}

probe_desktop() {
  local name="$1" url="$2"
  local body="$OUT/$name.html" code
  code=$(curl -sS -L --compressed --max-time 25 \
    -A "$DESK" \
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' \
    -H 'Accept-Language: en-US,en;q=0.9' \
    -H 'sec-ch-ua: "Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "Windows"' \
    -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' \
    -H 'Sec-Fetch-Site: none' -H 'Sec-Fetch-User: ?1' \
    -H 'Upgrade-Insecure-Requests: 1' \
    -H 'Referer: https://www.tiktok.com/' \
    -o "$body" -w '%{http_code}' "$url" 2>/dev/null)
  summarize "$name" "$body" "$code"
}

probe_mobile() {
  local name="$1" url="$2"
  local body="$OUT/$name.html" code
  code=$(curl -sS -L --compressed --max-time 25 \
    -A "$IPH" \
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
    -H 'Accept-Language: en-US,en;q=0.9' \
    -H 'Referer: https://www.tiktok.com/' \
    -o "$body" -w '%{http_code}' "$url" 2>/dev/null)
  summarize "$name" "$body" "$code"
}

echo "目标 handle：@${HANDLE}"
echo "输出目录：${OUT}"
echo

probe_desktop "desktop" "https://www.tiktok.com/@${HANDLE}"
sleep 3
probe_mobile  "iphone"  "https://www.tiktok.com/@${HANDLE}"
sleep 3
probe_mobile  "m-iphone" "https://m.tiktok.com/@${HANDLE}"
sleep 3
probe_desktop "with-lang" "https://www.tiktok.com/@${HANDLE}?lang=en"

echo
echo "==================== 汇总 ===================="
for i in "${!NAMES[@]}"; do
  printf '%-12s  HTTP %-3s  %7sB  universal=%s  waf=%s\n' \
    "${NAMES[$i]}" "${CODES[$i]}" "${SIZES[$i]}" "${UNIS[$i]}" "${WAFS[$i]}"
done
echo

FOUND=0
for i in "${!NAMES[@]}"; do
  if [ "${UNIS[$i]}" != "0" ]; then
    cp "$OUT/${NAMES[$i]}.html" "$HOME/profile.html"
    echo "✓ 找到真实页面：${NAMES[$i]} → 已保存为 ~/profile.html"
    FOUND=1
    break
  fi
done
[ "$FOUND" = "0" ] && echo "✗ 四种方式都只拿到 WAF 挑战页，没有真实数据"

echo
echo "建议：把 ~/probe-html/ 整个目录拉回本机再判断"
echo "scp -r ubuntu@<你的IP>:probe-html ./captured/"
