from __future__ import annotations

import pandas as pd

from .indicators import extract_indicators


INDICATOR_COLUMNS = [
    "sentiment_score",
    "war_escalation_score",
    "oil_supply_risk_score",
    "sanctions_score",
    "urgency_score",
    "chokepoint_risk_score",
    "kinetic_action_score",
    "policy_mechanism_score",
    "execution_certainty_score",
    "actionability",
    "matched_terms",
]


def summarize_event_study(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["topic", "mean_abnormal_return", "median_abnormal_return", "n_events"])

    return (
        df.groupby("topic", as_index=False)
        .agg(
            mean_abnormal_return=("abnormal_return", "mean"),
            median_abnormal_return=("abnormal_return", "median"),
            n_events=("abnormal_return", "size"),
        )
        .sort_values(["n_events", "mean_abnormal_return"], ascending=[False, False])
    )


def add_significance_flags(summary: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    out = summary.copy()
    if "p_value" not in out.columns:
        out["p_value"] = pd.NA
    out["is_significant"] = out["p_value"].apply(lambda p: bool(p < alpha) if pd.notna(p) else False)
    return out


def enrich_events_with_indicators(df: pd.DataFrame, text_col: str = "text") -> pd.DataFrame:
    out = df.copy()
    if text_col not in out.columns:
        out[text_col] = ""

    indicator_rows = [extract_indicators(str(text or "")) for text in out[text_col].tolist()]

    indicators_df = pd.DataFrame(indicator_rows)
    if indicators_df.empty:
        for col in INDICATOR_COLUMNS:
            if col not in out.columns:
                out[col] = pd.Series(dtype="object")
        return out

    for col in INDICATOR_COLUMNS:
        out[col] = indicators_df.get(col)

    return out
