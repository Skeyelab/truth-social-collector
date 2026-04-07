from datetime import datetime, timezone

from truthbrush_oil_study.truth_social import normalize_post


def test_normalize_post_preserves_timestamp_and_text():
    raw = {
        "id": "123",
        "created_at": "2024-01-02T03:04:05Z",
        "content": "Oil prices are too high!",
        "url": "https://truthsocial.com/@example/posts/123",
    }

    post = normalize_post(raw)

    assert post.id == "123"
    assert post.text == "Oil prices are too high!"
    assert post.created_at == datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert post.url == "https://truthsocial.com/@example/posts/123"
