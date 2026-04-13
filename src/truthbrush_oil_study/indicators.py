from __future__ import annotations

import re
from typing import Iterable

POSITIVE_TERMS = {
    "great",
    "successful",
    "success",
    "strong",
    "peace",
    "win",
    "winning",
    "good",
}

NEGATIVE_TERMS = {
    "disaster",
    "crisis",
    "failure",
    "weak",
    "threat",
    "chaos",
    "catastrophe",
    "war",
}

WAR_ESCALATION_TERMS = {
    "blockade",
    "strike",
    "eliminated",
    "eliminate",
    "navy",
    "naval",
    "ships",
    "missile",
    "attack",
    "military",
    "hormuz",
}

OIL_SUPPLY_RISK_TERMS = {
    "hormuz",
    "blockade",
    "ports",
    "port",
    "ocean",
    "sea",
    "oil",
    "tanker",
    "shipping",
    "exports",
}

SANCTIONS_TERMS = {
    "sanctions",
    "sanction",
    "embargo",
    "export controls",
    "tariffs",
    "penalties",
}

CHOKEPOINT_TERMS = {
    "hormuz",
    "strait",
    "shipping lane",
    "shipping lanes",
    "tanker",
    "tankers",
    "port",
    "ports",
    "blockade",
    "chokepoint",
}

KINETIC_ACTION_TERMS = {
    "strike",
    "strikes",
    "missile",
    "bomb",
    "attack",
    "intercept",
    "destroy",
    "eliminate",
    "eliminated",
    "naval",
    "military",
}

POLICY_MECHANISM_TERMS = {
    "sanctions",
    "embargo",
    "tariffs",
    "export controls",
    "executive order",
    "order",
    "ban",
    "restriction",
    "restrictions",
    "seizure",
}

EXECUTION_CERTAINTY_TERMS = {
    "effective immediately",
    "will",
    "will be",
    "begin",
    "begins",
    "starting",
    "tomorrow",
    "at ",
    "deadline",
}

URGENCY_TERMS = {
    "immediate",
    "immediately",
    "now",
    "urgent",
    "warning",
    "act now",
    "will be",
    "emergency",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z']+", text.lower()))


def _count_phrase_hits(text: str, terms: Iterable[str]) -> int:
    lowered = text.lower()
    hits = 0
    for term in terms:
        if term in lowered:
            hits += 1
    return hits


def _bounded_ratio(hits: int, full_scale_hits: int = 4) -> float:
    if hits <= 0:
        return 0.0
    return min(1.0, hits / float(full_scale_hits))


def _sentiment_score(text: str) -> float:
    tokens = _tokenize(text)
    pos = len(tokens & POSITIVE_TERMS)
    neg = len(tokens & NEGATIVE_TERMS)
    total = pos + neg
    if total == 0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / total))


def _actionability_label(
    war: float,
    oil: float,
    sanctions: float,
    urgency: float,
    chokepoint: float,
    kinetic: float,
    policy: float,
    execution: float,
) -> str:
    composite = (
        max(war, oil, sanctions, chokepoint, kinetic, policy) * 0.6
        + urgency * 0.2
        + execution * 0.2
    )
    if composite >= 0.6:
        return "high"
    if composite >= 0.2:
        return "medium"
    return "low"


def extract_indicators(text: str) -> dict:
    lowered = text.lower()

    war_hits = _count_phrase_hits(text, WAR_ESCALATION_TERMS)
    oil_hits = _count_phrase_hits(text, OIL_SUPPLY_RISK_TERMS)
    sanctions_hits = _count_phrase_hits(text, SANCTIONS_TERMS)
    urgency_hits = _count_phrase_hits(text, URGENCY_TERMS)

    chokepoint_hits = _count_phrase_hits(text, CHOKEPOINT_TERMS)
    kinetic_hits = _count_phrase_hits(text, KINETIC_ACTION_TERMS)
    policy_hits = _count_phrase_hits(text, POLICY_MECHANISM_TERMS)
    execution_hits = _count_phrase_hits(text, EXECUTION_CERTAINTY_TERMS)

    war_score = _bounded_ratio(war_hits)
    oil_score = _bounded_ratio(oil_hits)
    sanctions_score = _bounded_ratio(sanctions_hits, full_scale_hits=3)
    urgency_score = _bounded_ratio(urgency_hits, full_scale_hits=3)

    chokepoint_score = _bounded_ratio(chokepoint_hits, full_scale_hits=4)
    kinetic_score = _bounded_ratio(kinetic_hits, full_scale_hits=4)
    policy_score = _bounded_ratio(policy_hits, full_scale_hits=4)
    execution_score = _bounded_ratio(execution_hits, full_scale_hits=3)

    sentiment = _sentiment_score(text)

    actionability = _actionability_label(
        war_score,
        oil_score,
        sanctions_score,
        urgency_score,
        chokepoint_score,
        kinetic_score,
        policy_score,
        execution_score,
    )

    return {
        "sentiment_score": sentiment,
        "war_escalation_score": war_score,
        "oil_supply_risk_score": oil_score,
        "sanctions_score": sanctions_score,
        "urgency_score": urgency_score,
        "chokepoint_risk_score": chokepoint_score,
        "kinetic_action_score": kinetic_score,
        "policy_mechanism_score": policy_score,
        "execution_certainty_score": execution_score,
        "actionability": actionability,
        "matched_terms": {
            "war_escalation": [t for t in sorted(WAR_ESCALATION_TERMS) if t in lowered],
            "oil_supply_risk": [t for t in sorted(OIL_SUPPLY_RISK_TERMS) if t in lowered],
            "sanctions": [t for t in sorted(SANCTIONS_TERMS) if t in lowered],
            "urgency": [t for t in sorted(URGENCY_TERMS) if t in lowered],
            "chokepoint_risk": [t for t in sorted(CHOKEPOINT_TERMS) if t in lowered],
            "kinetic_action": [t for t in sorted(KINETIC_ACTION_TERMS) if t in lowered],
            "policy_mechanism": [t for t in sorted(POLICY_MECHANISM_TERMS) if t in lowered],
            "execution_certainty": [t for t in sorted(EXECUTION_CERTAINTY_TERMS) if t in lowered],
        },
    }
