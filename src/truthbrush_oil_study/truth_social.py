from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Iterable

from dateutil.parser import isoparse

from .models import Post


ENV_USERNAME = "TRUTHSOCIAL_USERNAME"
ENV_PASSWORD = "TRUTHSOCIAL_PASSWORD"
ENV_TOKEN = "TRUTHSOCIAL_TOKEN"


def normalize_post(raw: dict) -> Post:
    created_at = raw.get("created_at") or raw.get("createdAt") or raw.get("published_at")
    if created_at is None:
        raise ValueError("raw post is missing created_at")

    text = raw.get("content") or raw.get("text") or raw.get("body") or ""
    url = raw.get("url")
    if url is None and raw.get("id") is not None and raw.get("account", {}).get("username"):
        url = f"https://truthsocial.com/@{raw['account']['username']}/posts/{raw['id']}"

    dt = isoparse(created_at)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return Post(
        id=str(raw.get("id")),
        created_at=dt,
        text=str(text).strip(),
        url=url,
        raw=raw,
    )


def load_truthsocial_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env or os.environ)
    token = env.get(ENV_TOKEN)
    username = env.get(ENV_USERNAME)
    password = env.get(ENV_PASSWORD)
    if token:
        return env
    if not username or not password:
        raise RuntimeError(
            f"Set {ENV_USERNAME} and {ENV_PASSWORD}, or provide {ENV_TOKEN}."
        )
    return env


def truthbrush_command(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = load_truthsocial_env(env)
    return subprocess.run(
        ["truthbrush", *args],
        capture_output=True,
        text=True,
        env=full_env,
        check=True,
    )


def _parse_truthbrush_json_lines(stdout: str) -> Iterable[dict | list]:
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _extract_posts_from_page(page: dict | list) -> Iterable[dict]:
    if isinstance(page, list):
        for item in page:
            if isinstance(item, dict):
                yield item
        return

    for value in page.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield item


def fetch_user_statuses(
    username: str,
    *,
    replies: bool = False,
    pinned: bool = False,
    created_after: datetime | None = None,
    env: dict[str, str] | None = None,
) -> list[Post]:
    args = ["statuses", username]
    if replies:
        args.append("--replies")
    else:
        args.append("--no-replies")
    if pinned:
        args.append("--pinned")
    if created_after is not None:
        args.extend(["--created-after", created_after.isoformat()])

    result = truthbrush_command(*args, env=env)
    posts: list[Post] = []
    for page in _parse_truthbrush_json_lines(result.stdout):
        for raw_post in _extract_posts_from_page(page):
            posts.append(normalize_post(raw_post))
    return posts
