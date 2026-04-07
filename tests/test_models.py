from datetime import datetime, timezone

from truthbrush_oil_study.models import Post


def test_post_model_fields():
    post = Post(
        id="123",
        created_at=datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        text="hello",
        url="https://example.com/post/123",
    )

    assert post.id == "123"
    assert post.text == "hello"
    assert post.url == "https://example.com/post/123"
