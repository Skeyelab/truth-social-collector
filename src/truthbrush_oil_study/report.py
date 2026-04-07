from __future__ import annotations

import pandas as pd


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
