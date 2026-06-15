from __future__ import annotations

import re

from quantitative_sentiment_analysis.contracts.schemas import RelevanceLabel

_BTC_TERMS = (
    "btc",
    "btcusd",
    "bitcoin",
    "xbt",
)
_CRYPTO_TERMS = (
    "crypto",
    "cryptocurrency",
    "blockchain",
    "ethereum",
    "eth",
    "solana",
    "sol",
    "altcoin",
)
_NOISE_TERMS = (
    "sponsored",
    "advertisement",
    "promo",
    "placeholder",
    "test post",
    "duplicate",
)


def relevance_for_text(
    headline: str,
    body: str | None = None,
    *,
    source_id: str | None = None,
    source_name: str | None = None,
) -> RelevanceLabel:
    text = _normalize_text(" ".join(part for part in (headline, body or "") if part))
    if not text or _contains_any(text, _NOISE_TERMS):
        return RelevanceLabel.NOISE
    if not (source_id or source_name):
        return RelevanceLabel.NOISE
    if _contains_any(text, _BTC_TERMS):
        return RelevanceLabel.RELEVANT
    if _contains_any(text, _CRYPTO_TERMS):
        return RelevanceLabel.IRRELEVANT
    return RelevanceLabel.IRRELEVANT


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None
        for term in terms
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()
