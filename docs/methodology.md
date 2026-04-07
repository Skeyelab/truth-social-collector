# Methodology

## Question

Do presidential Truth Social posts coincide with short-horizon moves in oil futures?

## Data sources

- Truth Social posts pulled with `truthbrush`
- WTI and Brent futures prices from a market data source
- Optional calendar controls for EIA, CPI, FOMC, OPEC, and major geopolitical events

## Primary design

Use an event-study setup:

1. collect post timestamps
2. map each post to price windows before and after the post
3. compute returns for those windows
4. compare against matched baseline windows away from posts
5. summarize by topic

## Windows

Start with:
- 5 minutes
- 15 minutes
- 1 hour
- 1 day

## Topic buckets

Keep the first pass narrow:
- energy_policy
- geopolitics
- macro
- other

## Limitations

This is association, not causation.

Confounders are a real problem. Any serious interpretation needs controls for:
- scheduled economic releases
- inventory reports
- OPEC decisions
- war / sanctions news
- broad market moves

## Replication

1. Set Truth Social credentials in environment variables.
2. Pull posts.
3. Pull oil futures data.
4. Run the event-study summary.
5. Inspect topic-level outputs and plots.
