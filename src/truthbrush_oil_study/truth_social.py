from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from html import unescape
from typing import Iterable
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from dateutil.parser import isoparse

from .models import Post, ThreadContext


ENV_USERNAME = "TRUTHSOCIAL_USERNAME"
ENV_PASSWORD = "TRUTHSOCIAL_PASSWORD"
ENV_TOKEN = "TRUTHSOCIAL_TOKEN"
TRUMPSTRUTH_URL = "https://trumpstruth.org/"
TRUMPSTRUTH_TIMEZONE = "America/New_York"

_TRUMPSTRUTH_POST_RE = re.compile(
    r'href="https://trumpstruth\.org/statuses/(?P<status_id>\d+)"[^>]*>'
    r'(?P<display_time>[^<]+)</a>.*?'
    r'href="(?P<orig_url>https://truthsocial\.com/@realDonaldTrump/\d+)"[^>]*>\s*'
    r'(?:<i[^>]*></i>)?\s*&nbsp;\s*Original Post\s*</a>.*?'
    r'<div class="status__content"><p>(?P<content>.*?)</p>',
    re.S,
)


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


def _fetch_trumpstruth_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_trumpstruth_timestamp(display_time: str) -> datetime:
    naive = datetime.strptime(display_time.strip(), "%B %d, %Y, %I:%M %p")
    local_dt = naive.replace(tzinfo=ZoneInfo(TRUMPSTRUTH_TIMEZONE))
    return local_dt.astimezone(timezone.utc)


def _strip_html(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(unescape(text).split())


def parse_trumpstruth_homepage(html_text: str, *, limit: int | None = None) -> list[Post]:
    posts: list[Post] = []
    for match in _TRUMPSTRUTH_POST_RE.finditer(html_text):
        status_id = match.group("status_id")
        display_time = match.group("display_time")
        original_url = match.group("orig_url")
        content_html = match.group("content")
        post = Post(
            id=status_id,
            created_at=_parse_trumpstruth_timestamp(display_time),
            text=_strip_html(content_html),
            url=original_url,
            raw={
                "source": "trumpstruth.org",
                "status_url": f"https://trumpstruth.org/statuses/{status_id}",
                "display_time": display_time,
                "original_url": original_url,
            },
        )
        posts.append(post)
        if limit is not None and len(posts) >= limit:
            break
    return posts


def fetch_trumpstruth_posts(*, limit: int = 20, url: str = TRUMPSTRUTH_URL) -> list[Post]:
    html_text = _fetch_trumpstruth_html(url)
    return parse_trumpstruth_homepage(html_text, limit=limit)


def _build_api(env: dict[str, str] | None = None):
    """Instantiate a truthbrush Api object using credentials from *env*."""
    from truthbrush.api import Api

    full_env = load_truthsocial_env(env)
    return Api(
        username=full_env.get(ENV_USERNAME),
        password=full_env.get(ENV_PASSWORD),
        token=full_env.get(ENV_TOKEN),
    )


def _fetch_status_context(api, post_id: str) -> dict:
    """Fetch the full thread context (ancestors + descendants) for a status.

    This calls the ``/v1/statuses/{id}/context`` endpoint which returns a dict
    with ``"ancestors"`` and ``"descendants"`` lists.  The truthbrush library
    does not expose this endpoint through a public method, so we use its
    internal ``_get`` helper which applies the same authentication and rate-
    limiting logic as all other API calls.
    """
    result = api._get(f"/v1/statuses/{post_id}/context")
    return result if isinstance(result, dict) else {}


def fetch_post_thread(
    post_id: str,
    *,
    max_replies: int = 40,
    include_ancestors: bool = False,
    only_direct_replies: bool = False,
    env: dict[str, str] | None = None,
) -> ThreadContext:
    """Fetch thread context (replies and optionally ancestors) for a post.

    Descendants are fetched via the truthbrush API and deduped by status ID.
    Ancestors (parent posts up to the thread root) are fetched only when
    *include_ancestors* is ``True``.  Pagination is bounded by *max_replies*
    to prevent runaway collection.

    Args:
        post_id: The status ID whose thread context should be collected.
        max_replies: Maximum number of descendant replies to collect (default 40).
        include_ancestors: When ``True``, also fetch ancestor/parent posts.
        only_direct_replies: When ``True``, collect only direct replies to
            *post_id* rather than the full reply tree.
        env: Optional mapping of environment variables used for authentication.

    Returns:
        A :class:`~truthbrush_oil_study.models.ThreadContext` containing deduped
        ancestors and descendants.
    """
    api = _build_api(env)
    seen: set[str] = set()

    # --- descendants ---------------------------------------------------------
    descendants: list[Post] = []
    for raw in api.pull_comments(
        post_id,
        include_all=False,
        only_first=only_direct_replies,
        top_num=max_replies,
    ):
        if not isinstance(raw, dict):
            continue
        pid = str(raw.get("id") or "")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        try:
            descendants.append(normalize_post(raw))
        except (ValueError, KeyError):
            pass

    # --- ancestors (optional) ------------------------------------------------
    ancestors: list[Post] = []
    if include_ancestors:
        context = api._get(f"/v1/statuses/{post_id}/context")
        if isinstance(context, dict):
            for raw in context.get("ancestors") or []:
                if not isinstance(raw, dict):
                    continue
                aid = str(raw.get("id") or "")
                if not aid or aid in seen:
                    continue
                seen.add(aid)
                try:
                    ancestors.append(normalize_post(raw))
                except (ValueError, KeyError):
                    pass

    return ThreadContext(
        post_id=post_id,
        ancestors=tuple(ancestors),
        descendants=tuple(descendants),
    )
