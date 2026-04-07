import pandas as pd

from truthbrush_oil_study.report import summarize_event_study


def test_summarize_event_study_emits_core_metrics():
    df = pd.DataFrame(
        [
            {"topic": "energy_policy", "abnormal_return": 0.01},
            {"topic": "energy_policy", "abnormal_return": -0.02},
        ]
    )

    summary = summarize_event_study(df)

    assert "mean_abnormal_return" in summary.columns
    assert "n_events" in summary.columns
