"""TikTok 页面解析：HTML -> ProfileFacts。纯函数，无 I/O。"""
import json
import re
from typing import Optional

from .types import ProfileFacts

_SCOPE_RE = re.compile(
    r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
    re.S,
)
_WAF_MARKERS = ("_wafchallengeid", "Please wait...", "slardar-config")


class ParseError(Exception):
    pass


def looks_like_waf(html: str) -> bool:
    """WAF 挑战页：体积很小且带挑战标记。"""
    if not html:
        return False
    if len(html) > 20_000:
        return False
    return any(marker in html for marker in _WAF_MARKERS)


def _as_int(value) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        try:
            n = int(value)
            return n if n >= 0 else None
        except ValueError:
            return None
    return None


def parse_profile(html: str) -> ProfileFacts:
    """解析主页。找不到结构时抛 ParseError（由调用方判 error）。"""
    m = _SCOPE_RE.search(html or "")
    if not m:
        raise ParseError("no __UNIVERSAL_DATA_FOR_REHYDRATION__ script")

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        raise ParseError(f"bad embedded json: {exc}") from exc

    scope = data.get("__DEFAULT_SCOPE__") or {}
    detail = scope.get("webapp.user-detail") or {}
    info = detail.get("userInfo") or {}

    # statusCode 在 user-detail 层级（不在 userInfo 里），账号不存在时是 10221
    status_code = _as_int(detail.get("statusCode"))
    if status_code is None:
        status_code = _as_int(info.get("statusCode")) or 0
    user = info.get("user") or {}
    stats = info.get("stats") or {}

    if not user:
        # 账号不存在时 TikTok 仍返回 200，只是在 JSON 里给错误码
        if status_code:
            raise ParseError(f"user-detail statusCode={status_code}")
        raise ParseError("userInfo.user missing")

    unique_id = user.get("uniqueId") or ""
    if not unique_id:
        raise ParseError("uniqueId missing")

    signature = user.get("signature")
    return ProfileFacts(
        unique_id=unique_id,
        nickname=(user.get("nickname") or None),
        signature=signature if isinstance(signature, str) else None,
        avatar_url=(user.get("avatarLarger") or user.get("avatarMedium") or None),
        follower_count=_as_int(stats.get("followerCount")),
        following_count=_as_int(stats.get("followingCount")),
        likes_count=_as_int(stats.get("heartCount") or stats.get("heart")),
        video_count=_as_int(stats.get("videoCount")),
        private=bool(user.get("privateAccount")),
        verified=bool(user.get("verified")),
        status_code=status_code,
    )
