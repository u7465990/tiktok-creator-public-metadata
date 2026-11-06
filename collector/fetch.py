"""HTTP 抓取：限速、重试、快照缓存。"""
import hashlib
import json
import os
import random
import ssl
import time
import urllib.error
import urllib.request
from typing import Optional

from .types import Snapshot

IPHONE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)


class Fetcher:
    """单线程、带间隔的抓取器。缓存按 URL 内容寻址，支持断点续跑。"""

    def __init__(self, cache_dir: str, delay: float = 3.0, timeout: int = 30,
                 refresh: bool = False):
        self.cache_dir = cache_dir
        self.delay = delay
        self.timeout = timeout
        self.refresh = refresh
        self._last_request = 0.0
        os.makedirs(cache_dir, exist_ok=True)

    # ---------------- 缓存 ----------------
    def _key(self, url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()

    def _paths(self, url: str):
        key = self._key(url)
        return (
            os.path.join(self.cache_dir, key + ".html"),
            os.path.join(self.cache_dir, key + ".json"),
        )

    def _load(self, url: str) -> Optional[Snapshot]:
        body_path, meta_path = self._paths(url)
        if not (os.path.exists(body_path) and os.path.exists(meta_path)):
            return None
        try:
            meta = json.load(open(meta_path, encoding="utf-8"))
            body = open(body_path, encoding="utf-8", errors="ignore").read()
        except (OSError, ValueError):
            return None
        return Snapshot(
            url=url,
            status=int(meta.get("status", 0)),
            body=body,
            fetched_at=meta.get("fetched_at", ""),
            error=meta.get("error"),
            from_cache=True,
        )

    def _save(self, snap: Snapshot) -> None:
        body_path, meta_path = self._paths(snap.url)
        with open(body_path, "w", encoding="utf-8") as fh:
            fh.write(snap.body)
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(
                {"url": snap.url, "status": snap.status,
                 "fetched_at": snap.fetched_at, "error": snap.error},
                fh, ensure_ascii=False, indent=2,
            )

    # ---------------- 网络 ----------------
    def _sleep(self) -> None:
        if self._last_request:
            wait = self.delay + random.uniform(0, 1.0)
            elapsed = time.time() - self._last_request
            if elapsed < wait:
                time.sleep(wait - elapsed)

    def _request(self, url: str) -> Snapshot:
        req = urllib.request.Request(url, headers={
            "User-Agent": IPHONE_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
            "Referer": "https://www.tiktok.com/",
        })
        context = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=context) as resp:
                body = resp.read().decode("utf-8", errors="ignore")
                return Snapshot(url, resp.status, body, _now_utc())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore") if exc.fp else ""
            return Snapshot(url, exc.code, body, _now_utc())
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return Snapshot(url, 0, "", _now_utc(), error=f"{type(exc).__name__}: {exc}")

    def get(self, url: str) -> Snapshot:
        if not self.refresh:
            cached = self._load(url)
            if cached is not None and cached.status == 200:
                return cached

        snap = Snapshot(url, 0, "", _now_utc(), error="not attempted")
        for attempt in range(3):
            self._sleep()
            snap = self._request(url)
            self._last_request = time.time()
            if snap.status in (429,) or 500 <= snap.status < 600:
                time.sleep(2 * (attempt + 1))
                continue
            break

        self._save(snap)
        return snap


def _now_utc() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
