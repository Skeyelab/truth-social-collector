from __future__ import annotations

import json
from pathlib import Path

import typer

from .backtest import run_daily_backtest, run_term_indicator_scan
from .indicators import extract_indicators
from .report import summarize_event_study
from .topics import classify_post_topic
from .truth_social import fetch_trumpstruth_posts

app = typer.Typer(add_completion=False, help="Truth Social vs oil futures analysis pipeline")


@app.command()
def report(input_path: Path, output_path: Path | None = None) -> None:
    """Summarize an event-study CSV and print JSON."""
    import pandas as pd

    df = pd.read_csv(input_path)
    summary = summarize_event_study(df)
    if output_path is not None:
        summary.to_csv(output_path, index=False)
    typer.echo(json.dumps(summary.to_dict(orient="records"), default=str))


@app.command()
def signals(limit: int = 5) -> None:
    """Fetch latest trumpstruth posts and emit topic + indicator JSON records."""
    posts = fetch_trumpstruth_posts(limit=limit)
    payload = []
    for post in posts:
        indicators = extract_indicators(post.text)
        payload.append(
            {
                "id": post.id,
                "created_at": post.created_at.isoformat(),
                "url": post.url,
                "topic": classify_post_topic(post.text),
                **indicators,
                "text": post.text,
            }
        )
    typer.echo(json.dumps(payload, default=str))


@app.command("backtest-daily")
def backtest_daily(max_pages: int = 60, output_dir: Path | None = None) -> None:
    """Run daily volatility backtest and write artifacts to disk."""
    summary = run_daily_backtest(max_pages=max_pages, output_dir=output_dir)
    typer.echo(json.dumps(summary, default=str))


@app.command("backtest-terms")
def backtest_terms(
    output_dir: Path = typer.Option(..., help="Existing backtest output directory"),
    min_term_days: int = 4,
    min_non_term_days: int = 30,
) -> None:
    """Rank terms by next-day volatility lift using an existing backtest output dir."""
    summary = run_term_indicator_scan(
        output_dir=output_dir,
        min_term_days=min_term_days,
        min_non_term_days=min_non_term_days,
    )
    typer.echo(json.dumps(summary, default=str))


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
