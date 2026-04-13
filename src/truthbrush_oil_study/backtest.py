from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
import statsmodels.api as sm
from scipy.stats import ttest_ind

from .indicators import extract_indicators
from .truth_social import parse_trumpstruth_homepage

SYMBOLS = {"WTI": "CL=F", "Brent": "BZ=F"}


def _fetch_html(url: str, attempts: int = 3) -> str:
    last_error: Exception | None = None
    for i in range(attempts):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=30) as response:
                return response.read().decode("utf-8", "replace")
        except Exception as exc:  # pragma: no cover - network volatility
            last_error = exc
            time.sleep(1.0 + i)
    if last_error is not None:
        raise last_error
    raise RuntimeError("failed to fetch html")


def _collect_posts(max_pages: int) -> list:
    next_url = "https://trumpstruth.org/"
    seen_urls: set[str] = set()
    posts_by_id: dict[str, object] = {}

    for _ in range(max_pages):
        if not next_url or next_url in seen_urls:
            break
        seen_urls.add(next_url)

        html_text = _fetch_html(next_url)
        parsed = parse_trumpstruth_homepage(html_text, limit=None)
        for post in parsed:
            text = (post.text or "").strip()
            if not text or "Removed from Truth Social" in text:
                continue
            posts_by_id[post.id] = post

        match = re.search(r'href="([^"]+)"[^>]*>\s*Next Page\s*<', html_text, re.I)
        next_url = unescape(match.group(1)) if match else None

    return sorted(posts_by_id.values(), key=lambda p: p.created_at)


def _fetch_daily_prices(symbol: str, range_: str = "2y") -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range_}"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as response:
        payload = json.loads(response.read().decode())

    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp") or []
    closes = result["indicators"]["quote"][0].get("close") or []

    rows = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        date = pd.Timestamp(ts, unit="s", tz="UTC").normalize().date()
        rows.append({"date_utc": date, "close": float(close)})

    df = pd.DataFrame(rows).sort_values("date_utc").drop_duplicates("date_utc").reset_index(drop=True)
    df["return_1d"] = df["close"].pct_change()
    df["abs_return_1d"] = df["return_1d"].abs()
    df["next_return_1d"] = df["return_1d"].shift(-1)
    df["next_abs_return_1d"] = df["abs_return_1d"].shift(-1)
    return df


def _fit_models(df: pd.DataFrame, instrument: str, subset: str) -> tuple[dict, list[dict]]:
    y = df["next_abs_return_1d"]

    base_terms = ["post_count", "max_war_score", "max_oil_score", "max_urgency", "avg_sentiment"]
    expanded_terms = base_terms + [
        "max_chokepoint_score",
        "max_kinetic_score",
        "max_policy_score",
        "max_execution_score",
    ]

    x_base = sm.add_constant(df[base_terms], has_constant="add")
    x_expanded = sm.add_constant(df[expanded_terms], has_constant="add")

    model_base = sm.OLS(y, x_base).fit()
    model_expanded = sm.OLS(y, x_expanded).fit()

    summary = {
        "instrument": instrument,
        "subset": subset,
        "n_obs": int(model_base.nobs),
        "base_r2": model_base.rsquared,
        "base_adj_r2": model_base.rsquared_adj,
        "base_aic": model_base.aic,
        "expanded_r2": model_expanded.rsquared,
        "expanded_adj_r2": model_expanded.rsquared_adj,
        "expanded_aic": model_expanded.aic,
        "delta_adj_r2": model_expanded.rsquared_adj - model_base.rsquared_adj,
        "delta_aic": model_expanded.aic - model_base.aic,
    }

    coef_rows: list[dict] = []
    for term in ["const", *expanded_terms]:
        coef_rows.append(
            {
                "instrument": instrument,
                "subset": subset,
                "term": term,
                "coef": model_expanded.params.get(term, float("nan")),
                "p_value": model_expanded.pvalues.get(term, float("nan")),
            }
        )

    return summary, coef_rows


def run_daily_backtest(*, max_pages: int = 60, output_dir: Path | None = None) -> dict:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = output_dir or (Path("data/backtests") / run_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    posts = _collect_posts(max_pages=max_pages)
    if not posts:
        raise RuntimeError("No posts collected from trumpstruth.org")

    post_rows = []
    for post in posts:
        indicators = extract_indicators(post.text)
        post_rows.append(
            {
                "post_id": post.id,
                "ts_utc": pd.Timestamp(post.created_at),
                "date_utc": pd.Timestamp(post.created_at).date(),
                "text": post.text,
                "actionability": indicators["actionability"],
                "war_escalation_score": indicators["war_escalation_score"],
                "oil_supply_risk_score": indicators["oil_supply_risk_score"],
                "sanctions_score": indicators["sanctions_score"],
                "urgency_score": indicators["urgency_score"],
                "sentiment_score": indicators["sentiment_score"],
                "chokepoint_risk_score": indicators["chokepoint_risk_score"],
                "kinetic_action_score": indicators["kinetic_action_score"],
                "policy_mechanism_score": indicators["policy_mechanism_score"],
                "execution_certainty_score": indicators["execution_certainty_score"],
            }
        )

    posts_df = pd.DataFrame(post_rows)

    features = (
        posts_df.groupby("date_utc", as_index=False)
        .agg(
            post_count=("post_id", "size"),
            high_actionability_count=("actionability", lambda s: int((s == "high").sum())),
            max_war_score=("war_escalation_score", "max"),
            max_oil_score=("oil_supply_risk_score", "max"),
            max_urgency=("urgency_score", "max"),
            avg_sentiment=("sentiment_score", "mean"),
            max_chokepoint_score=("chokepoint_risk_score", "max"),
            max_kinetic_score=("kinetic_action_score", "max"),
            max_policy_score=("policy_mechanism_score", "max"),
            max_execution_score=("execution_certainty_score", "max"),
        )
        .sort_values("date_utc")
    )

    features["has_post"] = (features["post_count"] > 0).astype(int)
    features["has_high_actionability"] = (features["high_actionability_count"] > 0).astype(int)

    model_summaries: list[dict] = []
    coefficient_rows: list[dict] = []
    hi_comparison_rows: list[dict] = []

    for instrument, symbol in SYMBOLS.items():
        prices = _fetch_daily_prices(symbol)
        merged = prices.merge(features, on="date_utc", how="left")

        fill_zero_columns = [
            "post_count",
            "high_actionability_count",
            "max_war_score",
            "max_oil_score",
            "max_urgency",
            "avg_sentiment",
            "max_chokepoint_score",
            "max_kinetic_score",
            "max_policy_score",
            "max_execution_score",
            "has_post",
            "has_high_actionability",
        ]
        for column in fill_zero_columns:
            merged[column] = merged[column].fillna(0)

        full = merged.dropna(subset=["next_abs_return_1d"]).copy()
        window = full[
            (full["date_utc"] >= features["date_utc"].min())
            & (full["date_utc"] <= features["date_utc"].max())
        ].copy()

        for subset_name, subset_df in [("full", full), ("post_window", window)]:
            if len(subset_df) < 20:
                continue
            summary, coef_rows = _fit_models(subset_df, instrument, subset_name)
            model_summaries.append(summary)
            coefficient_rows.extend(coef_rows)

        hi = window[window["has_high_actionability"] == 1]["next_abs_return_1d"]
        lo = window[window["has_high_actionability"] == 0]["next_abs_return_1d"]
        t_stat = float("nan")
        p_value = float("nan")
        if len(hi) >= 2 and len(lo) >= 2:
            t_stat, p_value = ttest_ind(hi, lo, equal_var=False, nan_policy="omit")

        hi_comparison_rows.append(
            {
                "instrument": instrument,
                "n_hi_days": len(hi),
                "n_non_hi_days": len(lo),
                "mean_next_abs_return_hi": hi.mean() if len(hi) else float("nan"),
                "mean_next_abs_return_non_hi": lo.mean() if len(lo) else float("nan"),
                "delta_hi_minus_non_hi": (hi.mean() - lo.mean()) if len(hi) and len(lo) else float("nan"),
                "welch_t_stat": t_stat,
                "welch_p_value": p_value,
            }
        )

        merged.to_csv(out_dir / f"{instrument.lower()}_daily_merged.csv", index=False)

    model_df = pd.DataFrame(model_summaries)
    coef_df = pd.DataFrame(coefficient_rows)
    hi_df = pd.DataFrame(hi_comparison_rows)

    posts_df.to_csv(out_dir / "posts_with_indicators.csv", index=False)
    features.to_csv(out_dir / "daily_post_features.csv", index=False)
    model_df.to_csv(out_dir / "model_comparison.csv", index=False)
    coef_df.to_csv(out_dir / "expanded_model_coefficients.csv", index=False)
    hi_df.to_csv(out_dir / "high_actionability_comparison_post_window.csv", index=False)

    summary = {
        "run_id": run_id,
        "output_dir": str(out_dir),
        "posts": int(len(posts_df)),
        "days_with_posts": int(len(features)),
        "post_span_start": str(posts_df["ts_utc"].min()),
        "post_span_end": str(posts_df["ts_utc"].max()),
    }

    (out_dir / "SUMMARY.txt").write_text(json.dumps(summary, indent=2))
    return summary


_TERM_STOPWORDS = {
    "about", "after", "again", "against", "also", "among", "and", "any", "are", "around",
    "because", "been", "before", "being", "below", "between", "both", "but", "can", "could",
    "during", "each", "few", "from", "further", "have", "having", "here", "into", "its",
    "itself", "just", "more", "most", "much", "must", "near", "only", "other", "over",
    "own", "same", "should", "some", "such", "than", "that", "their", "theirs", "them",
    "then", "there", "these", "they", "this", "those", "through", "under", "until", "very",
    "what", "when", "where", "which", "while", "with", "would", "your", "yours", "president",
    "thank", "attention", "matter",
}


def _extract_terms(text: str) -> set[str]:
    terms = set()
    for token in re.findall(r"[a-zA-Z']+", (text or "").lower()):
        if len(token) < 4:
            continue
        if token in _TERM_STOPWORDS:
            continue
        terms.add(token)
    return terms


def run_term_indicator_scan(
    *,
    output_dir: Path,
    min_term_days: int = 4,
    min_non_term_days: int = 30,
) -> dict:
    posts_path = output_dir / "posts_with_indicators.csv"
    wti_path = output_dir / "wti_daily_merged.csv"
    brent_path = output_dir / "brent_daily_merged.csv"

    if not posts_path.exists():
        raise FileNotFoundError(f"Missing required file: {posts_path}")
    if not wti_path.exists() or not brent_path.exists():
        raise FileNotFoundError("Missing merged daily files for WTI/Brent")

    posts = pd.read_csv(posts_path)
    if "date_utc" not in posts.columns or "text" not in posts.columns:
        raise ValueError("posts_with_indicators.csv must contain date_utc and text")

    posts["date_utc"] = pd.to_datetime(posts["date_utc"]).dt.date
    posts["text"] = posts["text"].fillna("")

    term_days: dict[str, set] = {}
    for day, group in posts.groupby("date_utc"):
        day_terms: set[str] = set()
        for txt in group["text"]:
            day_terms |= _extract_terms(str(txt))
        for term in day_terms:
            term_days.setdefault(term, set()).add(day)

    term_days = {t: ds for t, ds in term_days.items() if len(ds) >= min_term_days}

    markets = {
        "WTI": pd.read_csv(wti_path),
        "Brent": pd.read_csv(brent_path),
    }

    per_market_rows: list[dict] = []
    for instrument, market_df in markets.items():
        if "date_utc" not in market_df.columns or "next_abs_return_1d" not in market_df.columns:
            raise ValueError(f"{instrument} merged file missing required columns")
        market_df["date_utc"] = pd.to_datetime(market_df["date_utc"]).dt.date
        market_df = market_df.dropna(subset=["next_abs_return_1d"])

        for term, days in term_days.items():
            yes = market_df[market_df["date_utc"].isin(days)]["next_abs_return_1d"]
            no = market_df[~market_df["date_utc"].isin(days)]["next_abs_return_1d"]

            if len(yes) < min_term_days or len(no) < min_non_term_days:
                continue

            t_stat, p_value = ttest_ind(yes, no, equal_var=False, nan_policy="omit")
            per_market_rows.append(
                {
                    "term": term,
                    "instrument": instrument,
                    "n_term_days": int(len(yes)),
                    "n_non_term_days": int(len(no)),
                    "mean_term": float(yes.mean()),
                    "mean_non_term": float(no.mean()),
                    "delta": float(yes.mean() - no.mean()),
                    "welch_t_stat": float(t_stat),
                    "p_value": float(p_value),
                }
            )

    market_df = pd.DataFrame(per_market_rows)
    if market_df.empty:
        out_path = output_dir / "term_indicator_candidates.csv"
        pd.DataFrame(
            columns=[
                "term",
                "days_wti",
                "days_brent",
                "delta_wti",
                "delta_brent",
                "avg_delta",
                "max_p",
            ]
        ).to_csv(out_path, index=False)
        return {"output_dir": str(output_dir), "rows": 0, "top_term": None, "path": str(out_path)}

    combined_rows: list[dict] = []
    for term, group in market_df.groupby("term"):
        if set(group["instrument"]) != {"WTI", "Brent"}:
            continue
        g = group.set_index("instrument")
        combined_rows.append(
            {
                "term": term,
                "days_wti": int(g.loc["WTI", "n_term_days"]),
                "days_brent": int(g.loc["Brent", "n_term_days"]),
                "delta_wti": float(g.loc["WTI", "delta"]),
                "delta_brent": float(g.loc["Brent", "delta"]),
                "avg_delta": float((g.loc["WTI", "delta"] + g.loc["Brent", "delta"]) / 2.0),
                "max_p": float(max(g.loc["WTI", "p_value"], g.loc["Brent", "p_value"])),
            }
        )

    combined = pd.DataFrame(combined_rows).sort_values(["avg_delta", "max_p"], ascending=[False, True])
    out_path = output_dir / "term_indicator_candidates.csv"
    combined.to_csv(out_path, index=False)

    top_term = combined.iloc[0]["term"] if not combined.empty else None
    return {
        "output_dir": str(output_dir),
        "rows": int(len(combined)),
        "top_term": top_term,
        "path": str(out_path),
    }
