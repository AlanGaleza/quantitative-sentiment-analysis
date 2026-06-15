from __future__ import annotations

from quantitative_sentiment_analysis.contracts.schemas import RelevanceLabel


def classification_confidence(
    sentiment_score: float,
    relevance: RelevanceLabel,
    *,
    headline: str,
    source_id: str | None = None,
    source_name: str | None = None,
) -> float:
    score_strength = min(1.0, abs(sentiment_score))
    confidence = 0.35 + (score_strength * 0.40)

    if relevance is RelevanceLabel.RELEVANT:
        confidence += 0.15
    elif relevance is RelevanceLabel.NOISE:
        confidence -= 0.15
    else:
        confidence -= 0.05

    if headline.strip():
        confidence += 0.05
    else:
        confidence -= 0.10

    if source_id or source_name:
        confidence += 0.05
    else:
        confidence -= 0.10

    return round(max(0.0, min(1.0, confidence)), 4)
