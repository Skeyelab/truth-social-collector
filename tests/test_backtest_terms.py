from pathlib import Path

import pandas as pd

from truthbrush_oil_study.backtest import run_term_indicator_scan


def test_run_term_indicator_scan_writes_candidates(tmp_path: Path):
    out = tmp_path / "run"
    out.mkdir(parents=True, exist_ok=True)

    posts = pd.DataFrame(
        [
            {"date_utc": "2026-04-01", "text": "Hormuz blockade and shipping lane risk"},
            {"date_utc": "2026-04-02", "text": "No issue today"},
            {"date_utc": "2026-04-03", "text": "Hormuz tanker route under pressure"},
            {"date_utc": "2026-04-04", "text": "Hormuz strait closure warning"},
            {"date_utc": "2026-04-05", "text": "hormuz blockade again"},
        ]
    )
    posts.to_csv(out / "posts_with_indicators.csv", index=False)

    def mk_daily(name: str):
        days = pd.date_range("2026-03-20", periods=25, freq="D")
        values = [0.01 + (i % 5) * 0.002 for i in range(25)]
        df = pd.DataFrame(
            {
                "date_utc": days.date.astype(str),
                "next_abs_return_1d": values,
            }
        )
        # make term days hotter (and non-identical)
        hot_values = {
            "2026-04-01": 0.050,
            "2026-04-03": 0.053,
            "2026-04-04": 0.056,
            "2026-04-05": 0.059,
        }
        for hot_day, hot_val in hot_values.items():
            df.loc[df["date_utc"] == hot_day, "next_abs_return_1d"] = hot_val
        df.to_csv(out / f"{name}_daily_merged.csv", index=False)

    mk_daily("wti")
    mk_daily("brent")

    summary = run_term_indicator_scan(output_dir=out, min_term_days=4, min_non_term_days=5)

    assert summary["rows"] > 0
    assert (out / "term_indicator_candidates.csv").exists()
