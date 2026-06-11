from __future__ import annotations

from collections.abc import Iterable


ALLOWED_PRODUCT_TERMS: tuple[str, ...] = (
    "BACKTEST-only",
    "analytical dataset",
    "ML dataset",
    "directional bias",
    "LONG",
    "SHORT",
    "FLAT",
    "classification confidence",
    "not an investment recommendation",
    "not an executable trading signal",
)

BANNED_PRODUCT_TERMS: tuple[str, ...] = (
    "trading signal",
    "signal generation",
    "buy recommendation",
    "sell recommendation",
    "investment recommendation",
    "trade now",
    "execute trade",
    "place order",
    "broker integration",
    "live-ready",
    "guaranteed profit",
)


class SemanticSafetyError(ValueError):
    """Raised when product-facing copy uses banned execution/advice wording."""


def find_banned_terms(
    text: str,
    *,
    exempt_terms: Iterable[str] = (),
) -> tuple[str, ...]:
    normalized_text = text.casefold()
    exempt = {term.casefold() for term in exempt_terms}
    return tuple(
        term
        for term in BANNED_PRODUCT_TERMS
        if term.casefold() not in exempt and term.casefold() in normalized_text
    )


def assert_semantic_safety(
    text: str,
    *,
    exempt_terms: Iterable[str] = (),
) -> None:
    banned_terms = find_banned_terms(text, exempt_terms=exempt_terms)
    if banned_terms:
        joined_terms = ", ".join(banned_terms)
        raise SemanticSafetyError(f"banned product-facing wording found: {joined_terms}")
