import json, re

html = open(r"tools\captured\probe-html\iphone.html", encoding="utf-8", errors="ignore").read()
m = re.search(r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
info = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]

items = info.get("itemList", [])
print("itemList 条数:", len(items))
if items:
    it = items[0]
    print("单条视频的键:", list(it)[:25])
    for k in ("desc", "id", "createTime", "stats", "video"):
        v = it.get(k, "<缺失>")
        if isinstance(v, (dict, list)):
            v = str(v)[:160]
        elif isinstance(v, str) and len(v) > 120:
            v = v[:120] + "..."
        print(f"  {k:10} = {v!r}")
    print("\n最近几条 desc:")
    for it2 in items[:3]:
        print("  -", repr(it2.get("desc", ""))[:140])

print("\navatarLarger 完整值:")
print(" ", info["user"].get("avatarLarger", "<缺失>")[:200])

print("\nstatsV2 键:", list(info.get("statsV2", {}))[:20])
print("shareMeta:", str(info.get("shareMeta"))[:200])
