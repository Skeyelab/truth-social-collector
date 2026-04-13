from truthbrush_oil_study.indicators import extract_indicators


def test_extract_indicators_sentiment_polarity():
    pos = extract_indicators("Great successful peace deal and strong growth")
    neg = extract_indicators("Disaster crisis failure and weak economy")

    assert pos["sentiment_score"] > 0
    assert neg["sentiment_score"] < 0


def test_extract_indicators_war_escalation_and_oil_risk():
    text = "Navy blockade at sea near Hormuz ports. Ships will be eliminated."
    out = extract_indicators(text)

    assert out["war_escalation_score"] > 0.5
    assert out["oil_supply_risk_score"] > 0.5
    assert out["urgency_score"] > 0


def test_extract_indicators_sanctions_score():
    out = extract_indicators("New sanctions and embargo pressure on exports")

    assert out["sanctions_score"] > 0.5


def test_extract_indicators_actionability_levels():
    high = extract_indicators("Immediate naval blockade in Hormuz. Act now.")
    medium = extract_indicators("Possible sanctions package under discussion.")
    low = extract_indicators("Happy birthday to everyone. Have a great day.")

    assert high["actionability"] == "high"
    assert medium["actionability"] in {"medium", "high"}
    assert low["actionability"] == "low"


def test_extract_indicators_new_scores_present_and_bounded():
    out = extract_indicators(
        "Strait of Hormuz shipping lane closure likely. "
        "Naval strike package is ready and effective immediately. "
        "Sanctions and embargo on exports begin tomorrow."
    )

    assert "chokepoint_risk_score" in out
    assert "kinetic_action_score" in out
    assert "policy_mechanism_score" in out
    assert "execution_certainty_score" in out

    assert 0.0 <= out["chokepoint_risk_score"] <= 1.0
    assert 0.0 <= out["kinetic_action_score"] <= 1.0
    assert 0.0 <= out["policy_mechanism_score"] <= 1.0
    assert 0.0 <= out["execution_certainty_score"] <= 1.0


def test_extract_indicators_chokepoint_kinetic_policy_execution_signal_strength():
    out = extract_indicators(
        "Blockade at the Strait of Hormuz. Naval strike operations begin. "
        "Executive order effective immediately. Sanctions and embargo on oil exports."
    )

    assert out["chokepoint_risk_score"] >= 0.6
    assert out["kinetic_action_score"] >= 0.5
    assert out["policy_mechanism_score"] >= 0.5
    assert out["execution_certainty_score"] >= 0.5
