import json

from typer.testing import CliRunner

from truthbrush_oil_study.cli import app


runner = CliRunner()


def test_backtest_terms_command_outputs_summary_json(monkeypatch):
    def fake_run_term_indicator_scan(*, output_dir, min_term_days=4, min_non_term_days=30):
        return {
            "output_dir": str(output_dir),
            "rows": 42,
            "top_term": "hormuz",
        }

    monkeypatch.setattr("truthbrush_oil_study.cli.run_term_indicator_scan", fake_run_term_indicator_scan)

    result = runner.invoke(
        app,
        [
            "backtest-terms",
            "--output-dir",
            "data/backtests/20260413_181242",
            "--min-term-days",
            "4",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["rows"] == 42
    assert payload["top_term"] == "hormuz"
