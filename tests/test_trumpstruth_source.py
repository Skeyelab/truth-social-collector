from datetime import timezone

from truthbrush_oil_study import truth_social


SAMPLE_HTML = """
<div class="status-info__meta-item">@realDonaldTrump</a> ·
  <a href="https://trumpstruth.org/statuses/37744" class="status-info__meta-item">April 13, 2026, 10:23 AM</a>
</div>
<div class="status-header__right">
  <a href="https://truthsocial.com/@realDonaldTrump/116397847496142849" target="_blank" class="status__external-link">
    <i class="fa-solid fa-arrow-up-right-from-square"></i>&nbsp; Original Post
  </a>
</div>
<div class="status__body">
  <div class="status__content"><p>Iran’s Navy is laying at the bottom of the sea. <a href="https://example.com/story">Read more</a></p></div>
</div>
"""


def test_parse_trumpstruth_homepage_extracts_post_fields():
    posts = truth_social.parse_trumpstruth_homepage(SAMPLE_HTML)

    assert len(posts) == 1
    post = posts[0]
    assert post.id == "37744"
    assert post.url == "https://truthsocial.com/@realDonaldTrump/116397847496142849"
    assert "Iran’s Navy is laying at the bottom of the sea." in post.text
    assert post.created_at.tzinfo is not None
    assert post.created_at.astimezone(timezone.utc).isoformat().startswith("2026-04-13T14:23:00")


def test_fetch_trumpstruth_posts_uses_html_fetcher(monkeypatch):
    monkeypatch.setattr(truth_social, "_fetch_trumpstruth_html", lambda _url: SAMPLE_HTML)

    posts = truth_social.fetch_trumpstruth_posts(limit=1)

    assert len(posts) == 1
    assert posts[0].id == "37744"


def test_fetch_trumpstruth_html_sends_browser_user_agent(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b"<html>ok</html>"

    captured = {}

    def fake_urlopen(req, timeout=20):
        captured["user_agent"] = req.headers.get("User-agent")
        return FakeResponse()

    monkeypatch.setattr(truth_social, "urlopen", fake_urlopen)

    html = truth_social._fetch_trumpstruth_html("https://trumpstruth.org/")

    assert html == "<html>ok</html>"
    assert captured["user_agent"]
    assert "Mozilla" in captured["user_agent"]
