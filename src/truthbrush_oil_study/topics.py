from __future__ import annotations


def classify_post_topic(text: str) -> str:
    lowered = text.lower()

    if any(keyword in lowered for keyword in ["drill", "oil", "gas prices", "energy", "fossil"]):
        return "energy_policy"
    if any(keyword in lowered for keyword in ["iran", "russia", "sanction", "war", "opec", "middle east"]):
        return "geopolitics"
    if any(keyword in lowered for keyword in ["inflation", "fed", "rates", "cpi", "jobs report"]):
        return "macro"
    return "other"
