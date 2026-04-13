import json

from typer.testing import CliRunner

from truthbrush_oil_study.cli import app


runner = CliRunner()


def test_backtest_daily_command_outputs_summary_json(monkeypatch):
    def fake_run_daily_backtest(*, max_pages=60, output_dir=None):
        return {
            "run_id": "20260413_000000",
            "output_dir": "data/backtests/20260413_000000",
            "posts": 123,
            "days_with_posts": 40,
        }

    monkeypatch.setattr("truthbrush_oil_study.cli.run_daily_backtest", fake_run_daily_backtest)

    result = runner.invoke(app, ["backtest-daily", "--max-pages", "5"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["run_id"] == "20260413_000000"
    assert payload["posts"] == 123
