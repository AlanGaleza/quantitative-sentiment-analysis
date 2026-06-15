from __future__ import annotations

import pytest

from quantitative_sentiment_analysis.contracts import (
    ALLOWED_PRODUCT_TERMS,
    BANNED_PRODUCT_TERMS,
    SemanticSafetyError,
    assert_semantic_safety,
    find_banned_terms,
)


def test_allowed_terms_include_backtest_analytical_framing() -> None:
    assert "BACKTEST-only" in ALLOWED_PRODUCT_TERMS
    assert "analytical dataset" in ALLOWED_PRODUCT_TERMS
    assert "directional bias" in ALLOWED_PRODUCT_TERMS
    assert {"LONG", "SHORT", "FLAT"}.issubset(set(ALLOWED_PRODUCT_TERMS))


def test_banned_terms_include_execution_and_advice_framing() -> None:
    assert "investment recommendation" in BANNED_PRODUCT_TERMS
    assert "execute trade" in BANNED_PRODUCT_TERMS
    assert "broker integration" in BANNED_PRODUCT_TERMS
    assert "live-ready" in BANNED_PRODUCT_TERMS


def test_find_banned_terms_is_case_insensitive() -> None:
    text = "This LIVE-ready trading signal can execute trade actions."

    assert find_banned_terms(text) == (
        "trading signal",
        "execute trade",
        "live-ready",
    )


def test_assert_semantic_safety_allows_backtest_analytical_copy() -> None:
    assert_semantic_safety(
        "BACKTEST-only analytical dataset with directional bias LONG, SHORT, "
        "or FLAT and classification confidence."
    )


def test_assert_semantic_safety_rejects_banned_product_copy() -> None:
    with pytest.raises(SemanticSafetyError, match="investment recommendation"):
        assert_semantic_safety("This is an investment recommendation.")


def test_safety_checks_support_explicit_historical_exemptions() -> None:
    text = "Historical notes may quote trading signal as a banned term example."

    assert find_banned_terms(text, exempt_terms=["trading signal"]) == ()
    assert_semantic_safety(text, exempt_terms=["trading signal"])
