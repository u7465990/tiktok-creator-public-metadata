"""把抓好的页面塞进缓存，用于离线端到端测试。"""
import hashlib
import json
import os
import shutil
import sys

url, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
key = hashlib.sha1(url.encode("utf-8")).hexdigest()
cache = os.path.join(out, "cache")
os.makedirs(cache, exist_ok=True)
shutil.copy(src, os.path.join(cache, key + ".html"))
with open(os.path.join(cache, key + ".json"), "w", encoding="utf-8") as fh:
    json.dump({"url": url, "status": 200,
               "fetched_at": "2026-11-06T05:00:00Z", "error": None}, fh)
print("seeded", key)
