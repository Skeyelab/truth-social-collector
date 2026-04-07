from __future__ import annotations

import json
from pathlib import Path

import typer

from .report import summarize_event_study

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


def main() -> int:
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
