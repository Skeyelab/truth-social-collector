# Presidential Posts vs. Oil Futures Study

This project builds a reproducible event-study pipeline to test whether presidential Truth Social posts are associated with short-horizon moves in oil futures.

## What it does
- collects Truth Social posts via a browser-session extension or `truthbrush` where possible
- normalizes posts into a stable schema
- ingests oil price series
- computes event-window returns
- classifies posts into a small set of topic buckets
- generates summary tables and plots

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

The project installs the `truthbrush-oil-study` CLI and pulls Truth Social data through the `truthbrush` package.

## Credentials

Set one of:

```bash
export TRUTHSOCIAL_USERNAME=...
export TRUTHSOCIAL_PASSWORD=...
```

Or, if you already have a token:

```bash
export TRUTHSOCIAL_TOKEN=...
```

## Run tests

```bash
pytest
```

## First analysis pass

Start with:
- WTI
- Brent
- 5m / 15m / 1h / 1d windows
- a single account
- obvious control-day exclusions

Do not read causation into raw correlation.
