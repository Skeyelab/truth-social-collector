from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Post:
    id: str
    created_at: datetime
    text: str
    url: str | None = None
    raw: dict | None = None


@dataclass(frozen=True, slots=True)
class ThreadContext:
    """Thread context for a single target post.

    Attributes:
        post_id: ID of the target/root post being analyzed.
        ancestors: Parent posts ordered from oldest ancestor to the direct parent.
        descendants: Reply posts (deduped) associated with the target post.
    """

    post_id: str
    ancestors: tuple[Post, ...] = field(default_factory=tuple)
    descendants: tuple[Post, ...] = field(default_factory=tuple)
