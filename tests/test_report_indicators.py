import pandas as pd

from truthbrush_oil_study.report import enrich_events_with_indicators


def test_enrich_events_with_indicators_adds_indicator_columns():
    df = pd.DataFrame([
        {"post_id": "1", "text": "Immediate naval blockade in Hormuz."},
    ])

    out = enrich_events_with_indicators(df)

    assert "war_escalation_score" in out.columns
    assert "oil_supply_risk_score" in out.columns
    assert "chokepoint_risk_score" in out.columns
    assert "kinetic_action_score" in out.columns
    assert "policy_mechanism_score" in out.columns
    assert "execution_certainty_score" in out.columns
    assert "actionability" in out.columns
    assert out.loc[0, "actionability"] in {"medium", "high"}


def test_enrich_events_with_indicators_handles_empty_df():
    df = pd.DataFrame(columns=["post_id", "text"])

    out = enrich_events_with_indicators(df)

    assert out.empty
    assert "actionability" in out.columns


def test_enrich_events_with_indicators_handles_missing_text_column():
    df = pd.DataFrame([{"post_id": "1"}])

    out = enrich_events_with_indicators(df)

    assert "actionability" in out.columns
    assert out.loc[0, "actionability"] == "low"
