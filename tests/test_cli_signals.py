import json
from datetime import datetime, timezone

from typer.testing import CliRunner

from truthbrush_oil_study.cli import app
from truthbrush_oil_study.models import Post


runner = CliRunner()


def test_signals_command_outputs_indicator_records(monkeypatch):
    sample_post = Post(
        id="37744",
        created_at=datetime(2026, 4, 13, 14, 23, tzinfo=timezone.utc),
        text="Immediate naval blockade in Hormuz. Act now.",
        url="https://truthsocial.com/@realDonaldTrump/116397847496142849",
    )

    def fake_fetch(*, limit=5, url="https://trumpstruth.org/"):
        return [sample_post]

    monkeypatch.setattr("truthbrush_oil_study.cli.fetch_trumpstruth_posts", fake_fetch)

    result = runner.invoke(app, ["signals", "--limit", "1"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["id"] == "37744"
    assert payload[0]["actionability"] in {"medium", "high"}
    assert "chokepoint_risk_score" in payload[0]
    assert "kinetic_action_score" in payload[0]
    assert "policy_mechanism_score" in payload[0]
    assert "execution_certainty_score" in payload[0]
