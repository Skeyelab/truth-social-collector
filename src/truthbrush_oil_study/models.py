from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Post:
    id: str
    created_at: datetime
    text: str
    url: str | None = None
    raw: dict | None = None
