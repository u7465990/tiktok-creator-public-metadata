"""共享类型。"""
from dataclasses import dataclass
from typing import Optional

STATUSES = ("ok", "not_found", "private", "blocked", "error")


@dataclass
class Snapshot:
    """一次请求的原始结果。status=0 表示连接层失败。"""
    url: str
    status: int
    body: str
    fetched_at: str
    error: Optional[str] = None
    from_cache: bool = False


@dataclass
class ProfileFacts:
    """从页面 JSON 里提取到的事实。"""
    unique_id: str
    nickname: Optional[str] = None
    signature: Optional[str] = None
    avatar_url: Optional[str] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    likes_count: Optional[int] = None
    video_count: Optional[int] = None
    private: bool = False
    verified: bool = False
    status_code: int = 0
