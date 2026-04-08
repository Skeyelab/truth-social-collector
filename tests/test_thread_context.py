"""Tests for fetch_post_thread and ThreadContext model."""
from datetime import datetime, timezone

import pytest

from truthbrush_oil_study import truth_social
from truthbrush_oil_study.models import Post, ThreadContext


# ---------------------------------------------------------------------------
# ThreadContext model
# ---------------------------------------------------------------------------


def test_thread_context_defaults_to_empty_tuples():
    ctx = ThreadContext(post_id="1")
    assert ctx.ancestors == ()
    assert ctx.descendants == ()


def test_thread_context_is_immutable():
    ctx = ThreadContext(post_id="1")
    with pytest.raises((AttributeError, TypeError)):
        ctx.post_id = "2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RAW_REPLY = {
    "id": "101",
    "created_at": "2024-01-01T00:01:00Z",
    "content": "First reply",
    "in_reply_to_id": "100",
}

_RAW_REPLY_2 = {
    "id": "102",
    "created_at": "2024-01-01T00:02:00Z",
    "content": "Second reply",
    "in_reply_to_id": "100",
}

_RAW_ANCESTOR = {
    "id": "50",
    "created_at": "2024-01-01T00:00:00Z",
    "content": "Ancestor post",
}


def _fake_api_factory(replies=(), context=None):
    """Return a minimal fake Api object."""

    class _FakeApi:
        def pull_comments(self, post, include_all, only_first, top_num):
            yield from replies

        def _get(self, url):
            return context or {}

    return _FakeApi()


# ---------------------------------------------------------------------------
# fetch_post_thread – descendants
# ---------------------------------------------------------------------------


def test_fetch_post_thread_returns_thread_context(monkeypatch):
    """Basic smoke test: returns a ThreadContext for the given post_id."""
    monkeypatch.setattr(
        truth_social, "_build_api", lambda env=None: _fake_api_factory()
    )

    ctx = truth_social.fetch_post_thread("100", env={"TRUTHSOCIAL_TOKEN": "tok"})

    assert isinstance(ctx, ThreadContext)
    assert ctx.post_id == "100"


def test_fetch_post_thread_normalizes_descendants(monkeypatch):
    monkeypatch.setattr(
        truth_social,
        "_build_api",
        lambda env=None: _fake_api_factory(replies=[_RAW_REPLY, _RAW_REPLY_2]),
    )

    ctx = truth_social.fetch_post_thread("100", env={"TRUTHSOCIAL_TOKEN": "tok"})

    assert len(ctx.descendants) == 2
    assert ctx.descendants[0].id == "101"
    assert ctx.descendants[1].id == "102"
    assert ctx.descendants[0].text == "First reply"


def test_fetch_post_thread_deduplicates_descendants(monkeypatch):
    """Duplicate reply entries (same id) must be collapsed."""
    monkeypatch.setattr(
        truth_social,
        "_build_api",
        # same reply emitted three times
        lambda env=None: _fake_api_factory(
            replies=[_RAW_REPLY, _RAW_REPLY, _RAW_REPLY]
        ),
    )

    ctx = truth_social.fetch_post_thread("100", env={"TRUTHSOCIAL_TOKEN": "tok"})

    assert len(ctx.descendants) == 1
    assert ctx.descendants[0].id == "101"


def test_fetch_post_thread_no_ancestors_by_default(monkeypatch):
    monkeypatch.setattr(
        truth_social, "_build_api", lambda env=None: _fake_api_factory()
    )

    ctx = truth_social.fetch_post_thread("100", env={"TRUTHSOCIAL_TOKEN": "tok"})

    assert ctx.ancestors == ()


def test_fetch_post_thread_respects_max_replies(monkeypatch):
    """max_replies is forwarded as top_num to pull_comments."""
    received = {}

    class _CountingApi:
        def pull_comments(self, post, include_all, only_first, top_num):
            received["top_num"] = top_num
            return iter([])

        def _get(self, url):
            return {}

    monkeypatch.setattr(truth_social, "_build_api", lambda env=None: _CountingApi())

    truth_social.fetch_post_thread("100", max_replies=5, env={"TRUTHSOCIAL_TOKEN": "tok"})

    assert received["top_num"] == 5


def test_fetch_post_thread_only_direct_replies_flag(monkeypatch):
    """only_direct_replies=True must be forwarded as only_first=True."""
    received = {}

    class _FlagApi:
        def pull_comments(self, post, include_all, only_first, top_num):
            received["only_first"] = only_first
            return iter([])

        def _get(self, url):
            return {}

    monkeypatch.setattr(truth_social, "_build_api", lambda env=None: _FlagApi())

    truth_social.fetch_post_thread(
        "100", only_direct_replies=True, env={"TRUTHSOCIAL_TOKEN": "tok"}
    )

    assert received["only_first"] is True


# ---------------------------------------------------------------------------
# fetch_post_thread – ancestors
# ---------------------------------------------------------------------------


def test_fetch_post_thread_fetches_ancestors_when_requested(monkeypatch):
    context = {"ancestors": [_RAW_ANCESTOR], "descendants": []}
    monkeypatch.setattr(
        truth_social,
        "_build_api",
        lambda env=None: _fake_api_factory(context=context),
    )

    ctx = truth_social.fetch_post_thread(
        "100", include_ancestors=True, env={"TRUTHSOCIAL_TOKEN": "tok"}
    )

    assert len(ctx.ancestors) == 1
    assert ctx.ancestors[0].id == "50"
    assert ctx.ancestors[0].text == "Ancestor post"


def test_fetch_post_thread_ancestors_deduped_against_descendants(monkeypatch):
    """An ancestor that shares an ID with a descendant should not appear twice."""
    duplicate = dict(_RAW_REPLY)  # id == "101"
    context = {"ancestors": [duplicate], "descendants": []}
    monkeypatch.setattr(
        truth_social,
        "_build_api",
        lambda env=None: _fake_api_factory(replies=[_RAW_REPLY], context=context),
    )

    ctx = truth_social.fetch_post_thread(
        "100", include_ancestors=True, env={"TRUTHSOCIAL_TOKEN": "tok"}
    )

    # id "101" is already in descendants; should not appear in ancestors too
    ancestor_ids = {p.id for p in ctx.ancestors}
    descendant_ids = {p.id for p in ctx.descendants}
    assert ancestor_ids.isdisjoint(descendant_ids)


def test_fetch_post_thread_skips_invalid_replies(monkeypatch):
    """Malformed reply dicts (missing created_at) must be skipped gracefully."""
    bad_reply = {"id": "999"}  # no created_at
    monkeypatch.setattr(
        truth_social,
        "_build_api",
        lambda env=None: _fake_api_factory(replies=[bad_reply, _RAW_REPLY]),
    )

    ctx = truth_social.fetch_post_thread("100", env={"TRUTHSOCIAL_TOKEN": "tok"})

    assert len(ctx.descendants) == 1
    assert ctx.descendants[0].id == "101"
