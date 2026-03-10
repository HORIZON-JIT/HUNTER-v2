"""Data models for HUNTER-v2."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TweetStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    FAILED = "failed"


class ContentType(str, Enum):
    SINGLE = "single"
    THREAD = "thread"


@dataclass
class Tweet:
    id: int | None = None
    content: str = ""
    content_type: str = ContentType.SINGLE
    thread_parts: list[str] = field(default_factory=list)
    status: str = TweetStatus.DRAFT
    theme: str = ""
    scheduled_at: datetime | None = None
    posted_at: datetime | None = None
    twitter_id: str | None = None  # ID returned from Twitter after posting
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ContentPlan:
    id: int | None = None
    week_start: str = ""  # ISO date string
    theme: str = ""
    content_type: str = ContentType.SINGLE
    description: str = ""
    priority: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Analytics:
    id: int | None = None
    tweet_id: int | None = None
    twitter_id: str | None = None
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    impressions: int = 0
    recorded_at: datetime = field(default_factory=datetime.now)


@dataclass
class ApiUsage:
    id: int | None = None
    provider: str = ""  # "twitter_official", "sociavault", "twitterapi_io"
    endpoint: str = ""
    cost_usd: float = 0.0
    recorded_at: datetime = field(default_factory=datetime.now)
