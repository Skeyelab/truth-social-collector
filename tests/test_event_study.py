from datetime import datetime, timezone

import pandas as pd

from truthbrush_oil_study.event_study import build_event_windows, compute_abnormal_returns


def test_build_event_windows_creates_pre_and_post_windows():
    posts = pd.DataFrame(
        [{"post_id": "1", "ts": datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)}]
    )

    windows = build_event_windows(posts, minutes_before=15, minutes_after=60)

    assert len(windows) == 1
    assert windows.iloc[0]["pre_window_minutes"] == 15
    assert windows.iloc[0]["post_window_minutes"] == 60


def test_compute_abnormal_returns_uses_pre_and_post_windows():
    event_windows = pd.DataFrame(
        [
            {
                "post_id": "1",
                "ts": datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc),
                "pre_window_minutes": 15,
                "post_window_minutes": 15,
            }
        ]
    )
    returns = pd.DataFrame(
        [
            {"ts": datetime(2024, 1, 2, 11, 50, tzinfo=timezone.utc), "return_1d": -0.01},
            {"ts": datetime(2024, 1, 2, 12, 5, tzinfo=timezone.utc), "return_1d": 0.03},
        ]
    )

    out = compute_abnormal_returns(event_windows, returns)

    assert round(out.iloc[0]["pre_return"], 6) == round(-0.01, 6)
    assert round(out.iloc[0]["post_return"], 6) == round(0.03, 6)
    assert round(out.iloc[0]["abnormal_return"], 6) == round(0.04, 6)
