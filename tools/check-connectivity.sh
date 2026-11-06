#!/usr/bin/env bash
# TikTok 采集连通性自检（只读）— macOS / Linux 版
# ------------------------------------------------------------
# 只判断"能不能采集"，不采集、不落库、不改任何东西。
# 依赖：curl（系统自带）+ 常见命令（dig / host / getent 任选其一做 DNS 检查）
# 用法：chmod +x check-connectivity.sh && ./check-connectivity.sh
# 可选：PROBE_HANDLE=tiktok TIMEOUT=25 ./check-connectivity.sh
# 输出：终端一张表 + check-output/connectivity-report.txt

set -u

PROBE_HANDLE="${PROBE_HANDLE:-tiktok}"
NOTFOUND_HANDLE="${NOTFOUND_HANDLE:-zzzz_no_such_user_9f3a2b}"
TIMEOUT="${TIMEOUT:-25}"
BASE="https://www.tiktok.com"
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SCRIPT_DIR/check-output"
mkdir -p "$OUT"
REPORT="$OUT/connectivity-report.txt"
: > "$REPORT"

say()  { printf '%s\n' "$*"; printf '%s\n' "$*" >> "$REPORT"; }
res()  { printf '  [%s] %-30s %s\n' "$1" "$2" "$3"; printf '  [%s] %-30s %s\n' "$1" "$2" "$3" >> "$REPORT"; }

say ""
say "=============================================================="
say " TikTok 采集连通性自检（只读，不采集任何数据）"
say " 时间：$(date '+%Y-%m-%d %H:%M:%S')   主机：$(hostname 2>/dev/null || echo unknown)"
say "=============================================================="
say ""

# ---------------------------------------------------------------- 0. 工具
if ! command -v curl >/dev/null 2>&1; then
  res FAIL "curl 可用" "找不到 curl，请先安装"
  say ""
  say "结论：无法执行自检。" 
  exit 2
fi
CURL_OK=1
res PASS "curl 可用" "$(curl --version 2>/dev/null | head -1)"

# ---------------------------------------------------------------- 探针
P_EXIT=0; P_CODE=0; P_URL=""; P_SIZE=0; P_TIME=""; P_TYPE=""; P_BODY=""; P_TEXT=""

probe() { # $1=url  $2=tag
  local url="$1" tag="$2" w
  P_BODY="$OUT/$tag.body.html"; local head="$OUT/$tag.headers.txt"
  w=$(curl -sS -L --compressed --max-redirs 5 --connect-timeout 10 --max-time "$TIMEOUT" \
        -A "$UA" \
        -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
        -H 'Accept-Language: en-US,en;q=0.9' \
        -H 'Referer: https://www.tiktok.com/' \
        -o "$P_BODY" -D "$head" \
        -w '%{http_code}|%{url_effective}|%{size_download}|%{time_total}|%{content_type}' \
        "$url" 2>/dev/null)
  P_EXIT=$?
  P_CODE=0; P_URL=""; P_SIZE=0; P_TIME=""; P_TYPE=""
  IFS='|' read -r c u s t ty <<< "$w"
  [ -n "${c:-}" ] && P_CODE="$c"
  P_URL="${u:-}"; P_TIME="${t:-}"; P_TYPE="${ty:-}"
  [ -f "$P_BODY" ] && P_SIZE=$(wc -c < "$P_BODY" | tr -d ' ')
  P_TEXT=""
  [ -f "$P_BODY" ] && P_TEXT=$(cat "$P_BODY" 2>/dev/null)
}

# ---------------------------------------------------------------- 1. 对照组
say "-- 1. 对照组（证明不是工具/网络整体坏了）--"
probe "https://example.com/" control
CONTROL_CODE="$P_CODE"
if [ "$P_CODE" = "200" ]; then
  res PASS "对照组 example.com" "HTTP 200，$P_SIZE 字节"
else
  res FAIL "对照组 example.com" "HTTP $P_CODE，curl 退出码 $P_EXIT（工具或整体网络异常）"
fi

# ---------------------------------------------------------------- 2. DNS
say ""
say "-- 2. DNS 解析 --"
DNS_IPS=""
if command -v dig >/dev/null 2>&1; then
  DNS_IPS=$(dig +short A www.tiktok.com 2>/dev/null | grep -E '^[0-9]+\.' | sort -u)
elif command -v host >/dev/null 2>&1; then
  DNS_IPS=$(host -t A www.tiktok.com 2>/dev/null | awk '/has address/{print $4}' | sort -u)
elif command -v getent >/dev/null 2>&1; then
  DNS_IPS=$(getent ahostsv4 www.tiktok.com 2>/dev/null | awk '{print $1}' | sort -u)
else
  DNS_IPS=$(nslookup www.tiktok.com 2>/dev/null | awk '/^Address: /{print $2}' | sort -u)
fi
DNS_SUSPECT=0
DNS_POLLUTED=0
if [ -z "$DNS_IPS" ]; then
  res FAIL "DNS 解析 www.tiktok.com" "解析失败（域名可能被污染或不可达）"
elif printf '%s\n' "$DNS_IPS" | grep -qE '^(10\.|127\.|0\.|169\.254\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)'; then
  DNS_SUSPECT=1
  res FAIL "DNS 解析 www.tiktok.com" "解析到非公网地址：$(echo $DNS_IPS | tr '\n' ' ')（典型 DNS 污染）"
elif printf '%s\n' "$DNS_IPS" | grep -qE '^(69\.171\.|31\.13\.|179\.60\.|157\.240\.|173\.252\.|66\.220\.|185\.60\.|8\.7\.198\.)'; then
  DNS_POLLUTED=1
  res FAIL "DNS 解析 www.tiktok.com" "解析到 Facebook/Meta 网段：$(echo $DNS_IPS | tr '\n' ' ')（DNS 被污染，不是 TikTok 的地址）"
else
  res PASS "DNS 解析 www.tiktok.com" "$(echo $DNS_IPS | tr '\n' ' ')"
fi

# ---------------------------------------------------------------- 3. 主页
say ""
say "-- 3. 主页探针（无登录）--"
URL="$BASE/@$PROBE_HANDLE"
say "  请求：$URL"
probe "$URL" profile
PROFILE_EXIT="$P_EXIT"; PROFILE_CODE="$P_CODE"; PROFILE_SIZE="$P_SIZE"; PROFILE_URL="$P_URL"; TEXT="$P_TEXT"

if [ "$P_EXIT" != "0" ]; then
  case "$P_EXIT" in
    6) EN="DNS 解析失败";; 7) EN="无法建立连接";; 28) EN="超时";;
    35) EN="TLS 握手失败";; 56) EN="接收数据失败";; *) EN="curl 错误";;
  esac
  res FAIL "HTTP 请求" "curl 退出码 $P_EXIT：$EN"
else
  res PASS "HTTP 请求" "HTTP $P_CODE，$P_SIZE 字节，${P_TIME}s"
fi

LOGIN=0; HAS_UNI=0; HAS_SIGI=0; HAS_FIELDS=0; CAPTCHA=0
if [ "$P_CODE" != "0" ]; then
  printf '%s' "$TEXT" | grep -q '__UNIVERSAL_DATA_FOR_REHYDRATION__' && HAS_UNI=1
  printf '%s' "$TEXT" | grep -q 'SIGI_STATE' && HAS_SIGI=1
  printf '%s' "$TEXT" | grep -qE '"followerCount"[[:space:]]*:[[:space:]]*[0-9]+' && HAS_FIELDS=1
  printf '%s' "$TEXT" | grep -q 'property="og:title"' && HAS_FIELDS=1
  printf '%s' "$TEXT" | grep -qiE 'captcha|Just a moment|_cf_chl|verify you are human' && CAPTCHA=1
  { case "$P_URL" in */login*) true;; *) false;; esac; } && LOGIN=1
  printf '%s' "$TEXT" | grep -qiE 'Log in to TikTok|login-modal' && LOGIN=1

  if [ "$LOGIN" = "1" ]; then res FAIL "是否跳登录" "被重定向/弹窗要求登录：$P_URL"
  else res PASS "是否跳登录" "未跳转，最终地址：$P_URL"; fi

  if [ "$CAPTCHA" = "1" ]; then res FAIL "验证码 / CF 挑战" "页面含验证码或 Cloudflare 挑战标记"
  else res PASS "验证码 / CF 挑战" "未检测到验证码标记"; fi

  if [ "$HAS_UNI" = "1" ]; then res PASS "结构化数据 UNIVERSAL" "找到 __UNIVERSAL_DATA_FOR_REHYDRATION__"
  elif [ "$HAS_SIGI" = "1" ]; then res WARN "结构化数据 UNIVERSAL" "只有旧版 SIGI_STATE，需兜底"
  else res WARN "结构化数据 UNIVERSAL" "未找到内嵌 JSON（可能靠 DOM/og 标签）"; fi

  if [ "$HAS_FIELDS" = "1" ]; then res PASS "关键字段" "页面含 followerCount 或 og:title"
  else res FAIL "关键字段" "未找到粉丝数/展示名字段"; fi

  if [ "$PROFILE_SIZE" -lt 5000 ] && [ "$HAS_UNI" = "0" ]; then
    res WARN "页面体积" "仅 $PROFILE_SIZE 字节，疑似软拦截空壳页"
  else
    res PASS "页面体积" "$PROFILE_SIZE 字节"
  fi
fi

# ---------------------------------------------------------------- 4. 不存在账号
if [ "$PROFILE_CODE" = "200" ]; then
  say ""
  say "-- 4. 不存在的账号（确认 404 还是 200+文案）--"
  sleep 2
  probe "$BASE/@$NOTFOUND_HANDLE" notfound
  NF_TEXT=0
  printf '%s' "$P_TEXT" | grep -qiE "Couldn't find this account|could not be found" && NF_TEXT=1
  res INFO "不存在账号的返回" "HTTP $P_CODE；含未找到文案：$NF_TEXT"
fi

# ---------------------------------------------------------------- 5. robots
say ""
say "-- 5. robots.txt --"
probe "$BASE/robots.txt" robots
ROBOTS_DISALLOW_PROFILE=0
if [ "$P_CODE" = "200" ]; then
  grep -E '^[[:space:]]*(User-agent|Allow|Disallow|Sitemap)' "$P_BODY" 2>/dev/null | head -30 | while IFS= read -r l; do say "    $l"; done
  if grep -qE '^Disallow:[[:space:]]*/[[:space:]]*$' "$P_BODY" 2>/dev/null && ! grep -qE '^Allow:[[:space:]]*/@' "$P_BODY" 2>/dev/null; then
    ROBOTS_DISALLOW_PROFILE=1
  fi
  if grep -qE '^Disallow:[[:space:]]*/@' "$P_BODY" 2>/dev/null; then ROBOTS_DISALLOW_PROFILE=1; fi
  if [ "$ROBOTS_DISALLOW_PROFILE" = "1" ]; then
    res WARN "robots 是否允许 /@" '"/" 被 Disallow 且无 Allow: /@ → 程序应记 blocked(robots_disallow)'
  else
    res PASS "robots 是否允许 /@" "未见针对 /@ 的禁止规则（仍需以原文为准）"
  fi
else
  res WARN "robots.txt" "HTTP $P_CODE，未取得原文"
fi

# ---------------------------------------------------------------- 6. 头像
if [ "$PROFILE_CODE" = "200" ] && printf '%s' "$TEXT" | grep -qE 'https://[^"'"'"' ]*tiktokcdn[^"'"'"' ]*'; then
  say ""
  say "-- 6. 头像 CDN --"
  AURL=$(printf '%s' "$TEXT" | grep -oE 'https://[^"'"'"' ]*tiktokcdn[^"'"'"' ]*' | head -1)
  w=$(curl -sS -L --connect-timeout 10 --max-time "$TIMEOUT" -A "$UA" \
        -H 'Referer: https://www.tiktok.com/' -r 0-4095 -o "$OUT/avatar.probe.bin" \
        -w '%{http_code}|%{content_type}' "$AURL" 2>/dev/null)
  ACODE="${w%%|*}"; ACTS="${w#*|}"
  case "$ACODE" in
    200|206) case "$ACTS" in image/*) res PASS "头像可匿名下载" "HTTP $ACODE，$ACTS";;
             *) res WARN "头像可匿名下载" "HTTP $ACODE，类型 $ACTS";; esac;;
    *) res WARN "头像可匿名下载" "HTTP ${ACODE}（可能校验 Referer 或已过期）";;
  esac
fi

# ---------------------------------------------------------------- 结论
say ""
say "-- 结论 --"
if [ "$CONTROL_CODE" != "200" ]; then
  VERDICT="本机网络整体异常（连 example.com 都不通）"
  ADVICE="先解决本机网络/代理，再谈 TikTok。"
  CODE=2
elif [ "$DNS_POLLUTED" = "1" ] || [ "$DNS_SUSPECT" = "1" ]; then
  VERDICT="DNS 被污染：拿到的是假地址"
  ADVICE="解析结果不属于 TikTok，重试/换 UA/降速都没用；换境外云主机或向招聘方申请环境。"
  CODE=2
elif [ "$PROFILE_EXIT" = "6" ] || [ "$PROFILE_EXIT" = "7" ] || [ "$PROFILE_EXIT" = "28" ] || [ "$PROFILE_EXIT" = "35" ]; then
  VERDICT="环境不可达：DNS/连接层被拦"
  ADVICE="这台机器无法访问 TikTok，不要在这里跑采集；换境外云主机或向招聘方申请运行环境。"
  CODE=2
elif [ "$PROFILE_CODE" = "403" ] || [ "$PROFILE_CODE" = "429" ]; then
  VERDICT="IP 被限流/封禁"
  ADVICE="降低频率、换网络出口；如实记 blocked，不要绕过。"
  CODE=1
elif [ "$LOGIN" = "1" ]; then
  VERDICT="需要登录才能看主页"
  ADVICE="按题面要求记 blocked，不要加 Cookie。"
  CODE=1
elif [ "$PROFILE_CODE" = "200" ] && [ "$HAS_FIELDS" = "1" ]; then
  if [ "$HAS_UNI" = "1" ]; then
    VERDICT="可用：可采集"
    ADVICE="走内嵌 JSON 解析；仍保留 og: 标签兜底。"
  else
    VERDICT="可用：可采集"
    ADVICE="没有内嵌 JSON，先用 og:title/og:description 兜底，再评估 DOM 解析。"
  fi
  CODE=0
elif [ "$PROFILE_CODE" = "200" ]; then
  VERDICT="页面可访问但未找到数据（疑似改版或软拦截）"
  ADVICE="保存的页面在 check-output/profile.body.html，发回来人工看一下。"
  CODE=1
else
  VERDICT="未知情况（HTTP $PROFILE_CODE，curl 退出码 $PROFILE_EXIT）"
  ADVICE="把 check-output 整个目录发回来。"
  CODE=1
fi

say "  判定：$VERDICT"
say "  → $ADVICE"
say ""
say "  产物目录：$OUT"
say "  （report + 抓到的页面原文；不含任何 Cookie/凭据）"
if [ "$ROBOTS_DISALLOW_PROFILE" = "1" ]; then
  say "  注意：robots 可能禁止主页抓取，程序里要做守卫并如实记 blocked。"
fi

exit "$CODE"
