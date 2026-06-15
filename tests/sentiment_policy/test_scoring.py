import pytest

from quantitative_sentiment_analysis.contracts.schemas import DirectionalBias
from quantitative_sentiment_analysis.sentiment_policy import (
    directional_bias_for_score,
    score_text,
)


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.20, DirectionalBias.LONG),
        (0.1999, DirectionalBias.FLAT),
        (0.0, DirectionalBias.FLAT),
        (-0.1999, DirectionalBias.FLAT),
        (-0.20, DirectionalBias.SHORT),
    ],
)
def test_directional_bias_threshold_boundaries(
    score: float,
    expected: DirectionalBias,
) -> None:
    assert directional_bias_for_score(score) is expected


@pytest.mark.parametrize("score", [float("inf"), float("-inf"), float("nan"), -1.01, 1.01])
def test_directional_bias_rejects_invalid_scores(score: float) -> None:
    with pytest.raises(ValueError):
        directional_bias_for_score(score)


def test_score_text_maps_positive_lexicon_to_long_bias() -> None:
    score = score_text("Bitcoin ETF approval drives institutional inflows")

    assert score > 0
    assert directional_bias_for_score(score) is DirectionalBias.LONG


def test_score_text_maps_negative_lexicon_to_short_bias() -> None:
    score = score_text("Bitcoin faces regulatory crackdown after exchange hack")

    assert score < 0
    assert directional_bias_for_score(score) is DirectionalBias.SHORT


def test_score_text_keeps_neutral_text_flat() -> None:
    score = score_text("Bitcoin market update published for Monday session")

    assert score == 0
    assert directional_bias_for_score(score) is DirectionalBias.FLAT


def test_score_text_is_bounded_and_deterministic() -> None:
    headline = "Bitcoin rally surge breakout with ETF approval and institutional inflows"

    first = score_text(headline)
    second = score_text(headline)

    assert first == second
    assert -1 <= first <= 1
