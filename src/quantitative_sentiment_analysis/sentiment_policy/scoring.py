from __future__ import annotations

from math import isfinite
import re

from quantitative_sentiment_analysis.contracts.schemas import DirectionalBias
from quantitative_sentiment_analysis.sentiment_policy.config import DEFAULT_POLICY_CONFIG

_POSITIVE_WEIGHTS: dict[str, float] = {
    "approval": 0.20,
    "adoption": 0.18,
    "accumulation": 0.18,
    "bullish": 0.30,
    "breakout": 0.24,
    "inflows": 0.22,
    "rally": 0.24,
    "surge": 0.22,
    "support": 0.14,
    "upgrade": 0.16,
    "etf approval": 0.35,
    "institutional inflows": 0.30,
}

_NEGATIVE_WEIGHTS: dict[str, float] = {
    "ban": -0.28,
    "bearish": -0.30,
    "crackdown": -0.30,
    "exploit": -0.28,
    "hack": -0.34,
    "lawsuit": -0.22,
    "liquidation": -0.24,
    "outflows": -0.22,
    "rejection": -0.20,
    "selloff": -0.30,
    "regulatory crackdown": -0.36,
}


def directional_bias_for_score(score: float) -> DirectionalBias:
    _validate_score(score)
    if score >= DEFAULT_POLICY_CONFIG.long_threshold:
        return DirectionalBias.LONG
    if score <= DEFAULT_POLICY_CONFIG.short_threshold:
        return DirectionalBias.SHORT
    return DirectionalBias.FLAT


def score_text(headline: str, body: str | None = None) -> float:
    text = _normalize_text(" ".join(part for part in (headline, body or "") if part))
    if not text:
        return 0.0

    score = 0.0
    for term, weight in _POSITIVE_WEIGHTS.items():
        if _contains_term(text, term):
            score += weight
    for term, weight in _NEGATIVE_WEIGHTS.items():
        if _contains_term(text, term):
            score += weight

    return round(max(-1.0, min(1.0, score)), 4)


def _validate_score(score: float) -> None:
    if not isfinite(score):
        raise ValueError("sentiment score must be finite")
    if score < -1 or score > 1:
        raise ValueError("sentiment score must be in -1..1")


def _contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term)
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text) is not None


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()
