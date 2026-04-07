from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd


@dataclass(frozen=True, slots=True)
class EventWindowSpec:
    minutes_before: int
    minutes_after: int


def build_event_windows(posts: pd.DataFrame, minutes_before: int, minutes_after: int) -> pd.DataFrame:
    out = posts.copy()
    out["pre_window_minutes"] = minutes_before
    out["post_window_minutes"] = minutes_after
    return out


def compute_abnormal_returns(event_windows: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    if "ts" not in event_windows.columns:
        raise ValueError("event_windows must contain ts")
    if "ts" not in returns.columns:
        raise ValueError("returns must contain ts")
    if "return_1d" not in returns.columns:
        raise ValueError("returns must contain return_1d")

    events = event_windows.copy()
    market = returns.copy()
    events["ts"] = pd.to_datetime(events["ts"], utc=True)
    market["ts"] = pd.to_datetime(market["ts"], utc=True)

    rows = []
    for _, event in events.iterrows():
        pre_minutes = int(event.get("pre_window_minutes", 0))
        post_minutes = int(event.get("post_window_minutes", 0))
        ts = event["ts"]

        pre_mask = (market["ts"] >= ts - timedelta(minutes=pre_minutes)) & (market["ts"] < ts)
        post_mask = (market["ts"] > ts) & (market["ts"] <= ts + timedelta(minutes=post_minutes))

        pre_return = market.loc[pre_mask, "return_1d"].mean()
        post_return = market.loc[post_mask, "return_1d"].mean()
        abnormal_return = post_return - pre_return if pd.notna(pre_return) and pd.notna(post_return) else pd.NA

        rows.append(
            {
                **event.to_dict(),
                "pre_return": pre_return,
                "post_return": post_return,
                "abnormal_return": abnormal_return,
            }
        )

    return pd.DataFrame(rows)
