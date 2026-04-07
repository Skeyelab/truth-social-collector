from types import SimpleNamespace

from truthbrush_oil_study import truth_social


def test_fetch_user_statuses_parses_truthbrush_pages(monkeypatch):
    stdout = """
    [{"id": "1", "created_at": "2024-01-01T00:00:00Z", "content": "First"}]
    [{"id": "2", "created_at": "2024-01-02T00:00:00Z", "content": "Second"}]
    """.strip()

    def fake_command(*args, **kwargs):
        return SimpleNamespace(stdout=stdout)

    monkeypatch.setattr(truth_social, "truthbrush_command", fake_command)

    posts = truth_social.fetch_user_statuses("hermes1234567", env={"TRUTHSOCIAL_TOKEN": "token"})

    assert [p.id for p in posts] == ["1", "2"]
    assert [p.text for p in posts] == ["First", "Second"]
