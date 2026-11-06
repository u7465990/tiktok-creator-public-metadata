"""handle 规范化、状态判定、结果组装。全部为纯函数。"""
import re
from datetime import datetime, timezone
from typing import Optional, Tuple

from .parse import ParseError, looks_like_waf, parse_profile
from .types import ProfileFacts, Snapshot

_URL_PREFIX = re.compile(r"^(?:https?://)?(?:www\.|m\.)?tiktok\.com/", re.I)


def normalize_handle(raw: str) -> str:
    """可重复、可解释的规范化：去协议/域名/查询串/@/末尾斜杠/大小写。"""
    s = (raw or "").strip()
    s = _URL_PREFIX.sub("", s)
    s = s.split("?")[0].split("#")[0]
    s = s.strip().rstrip("/")
    s = s.lstrip("@")
    return s.strip().lower()


def profile_url_for(normalized: str) -> str:
    return f"https://www.tiktok.com/@{normalized}"


def interpret(html: str) -> Tuple[str, Optional[ProfileFacts], Optional[str]]:
    """把页面内容解释成 (status, facts, error)。

    三分支：WAF 挑战 -> blocked；解析失败但含 statusCode -> not_found；其余 -> error。
    """
    if looks_like_waf(html):
        return "blocked", None, "waf_challenge: 页面是 WAF 挑战页，未取得内容"
    try:
        facts = parse_profile(html)
    except ParseError as exc:
        message = str(exc)
        if "statusCode=" in message:
            return "not_found", None, f"账号不存在（{message}）"
        return "error", None, f"解析失败：{message}"

    if facts.private:
        return "private", facts, "账号私密：内容不对未登录访客公开，元信息仍可见"
    return "ok", facts, None


def decide_status(snapshot: Snapshot) -> Tuple[str, Optional[ProfileFacts], Optional[str]]:
    """HTTP 层 + 内容层合成唯一结论。"""
    if snapshot.status == 0:
        return "error", None, snapshot.error or "连接失败"
    if snapshot.status in (403, 429):
        return "blocked", None, f"HTTP {snapshot.status}：被限流或拒绝"
    if snapshot.status >= 500:
        return "error", None, f"HTTP {snapshot.status}：对方服务异常"
    if snapshot.status == 404:
        return "not_found", None, "HTTP 404：账号不存在"
    return interpret(snapshot.body)


def build_record(
    handle: str,
    normalized: str,
    snapshot: Snapshot,
    status: str,
    facts: Optional[ProfileFacts],
    error: Optional[str],
    language: str,
    confidence: float,
    evidence: Optional[dict],
    avatar_file: Optional[str],
    now: Optional[str] = None,
) -> dict:
    """按题目 Schema 组装一条结果。三值 bio 与 null 策略集中在这里。"""
    now = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    bio = None
    if facts is not None and facts.signature is not None and status in ("ok", "private"):
        bio = facts.signature  # 保留空串：空简介 ≠ 没采到

    source_urls = []
    if snapshot.status and status != "error":
        source_urls = [snapshot.url]

    record = {
        "handle": handle,
        "normalized_handle": normalized,
        "profile_url": (f"https://www.tiktok.com/@{facts.unique_id}" if facts else None),
        "display_name": (facts.nickname if facts else None),
        "avatar_url": (facts.avatar_url if facts else None),
        "avatar_file": avatar_file,
        "bio": bio,
        "follower_count": (facts.follower_count if facts else None),
        "language": language,
        "language_confidence": confidence,
        "language_evidence": evidence,
        "source_urls": source_urls,
        "collected_at": now,
        "status": status,
        "error": error,
    }

    if facts is not None:
        record["following_count"] = facts.following_count
        record["likes_count"] = facts.likes_count
        record["video_count"] = facts.video_count
        record["verified"] = facts.verified

    return record
