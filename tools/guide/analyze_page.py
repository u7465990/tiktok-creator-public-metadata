import json, re, sys

path = r"tools\captured\probe-html\iphone.html"
html = open(path, encoding="utf-8", errors="ignore").read()
print("文件大小:", len(html), "字符")

m = re.search(r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
print("找到 UNIVERSAL script:", bool(m))
if not m:
    for marker in ("SIGI_STATE", "__DEFAULT_SCOPE__", "userInfo", "followerCount"):
        print(f"  {marker}: {html.count(marker)}")
    sys.exit(0)

data = json.loads(m.group(1))
print("顶层键:", list(data)[:10])
scope = data.get("__DEFAULT_SCOPE__", {})
print("defaultScope 键:", list(scope)[:20])

ud = scope.get("webapp.user-detail", {})
print("user-detail 键:", list(ud))

ui = ud.get("userInfo", {})
print("userInfo 键:", list(ui))

u = ui.get("user", {})
s = ui.get("stats", {})
print("\n--- user 字段（抽样）---")
for k in ("id", "uniqueId", "nickname", "signature", "avatarLarger", "avatarMedium",
          "avatarThumb", "privateAccount", "verified", "region", "secUid", "createTime"):
    v = u.get(k, "<缺失>")
    if isinstance(v, str) and len(v) > 90:
        v = v[:90] + "..."
    print(f"  {k:12} = {v!r}")

print("\n--- stats 字段 ---")
for k in ("followerCount", "followingCount", "heart", "heartCount", "videoCount", "diggCount"):
    if k in s:
        print(f"  {k:15} = {s[k]!r} (type={type(s[k]).__name__})")

print("\n--- 其他可用信号 ---")
for k in ("itemList", "user", "stats", "shareMeta"):
    print(f"  user-detail.{k}: {'有' if k in ud else '无'}")

og = dict(re.findall(r'<meta[^>]+property="og:(\w+)"[^>]+content="([^"]*)"', html))
print("\nog 标签:", {k: (v[:80] + "...") if len(v) > 80 else v for k, v in og.items()})

print("\n私有账号标志出现次数:", html.count('"privateAccount":true'))
print("视频列表关键字 itemList 出现次数:", html.count('"itemList"'))
