"""头像下载：匿名请求 + 内容类型校验 + 相对路径。"""
import os
import re
import ssl
import urllib.request
from typing import Optional, Tuple

from .fetch import IPHONE_UA

_EXT = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp", "gif": "gif"}


def slugify(normalized: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (normalized or "").lower()).strip("_")
    return (slug or "creator")[:60]


def download_avatar(url: str, dest_dir: str, slug: str,
                    timeout: int = 25) -> Tuple[Optional[str], Optional[str]]:
    """成功返回 ('avatars/<slug>.<ext>', None)，失败返回 (None, 原因)。"""
    req = urllib.request.Request(url, headers={
        "User-Agent": IPHONE_UA,
        "Referer": "https://www.tiktok.com/",
        "Accept": "image/avif,image/webp,image/*,*/*;q=0.8",
        "Accept-Encoding": "identity",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl.create_default_context()) as resp:
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            data = resp.read(5_000_000)
    except Exception as exc:  # noqa: BLE001 - 任何失败都只影响头像字段
        return None, f"{type(exc).__name__}: {exc}"

    if not ctype.startswith("image/"):
        return None, f"非图片响应（{ctype or 'unknown'}）"
    if len(data) < 500:
        return None, f"图片过小（{len(data)} 字节）"

    ext = _EXT.get(ctype.split("/")[-1], "jpg")
    os.makedirs(dest_dir, exist_ok=True)
    filename = f"{slug}.{ext}"
    with open(os.path.join(dest_dir, filename), "wb") as fh:
        fh.write(data)
    return f"avatars/{filename}", None
