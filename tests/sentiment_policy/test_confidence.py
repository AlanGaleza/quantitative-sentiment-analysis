from quantitative_sentiment_analysis.contracts.schemas import RelevanceLabel
from quantitative_sentiment_analysis.sentiment_policy import classification_confidence


def test_classification_confidence_is_bounded() -> None:
    confidence = classification_confidence(
        1.0,
        RelevanceLabel.RELEVANT,
        headline="Bitcoin rally",
        source_id="cryptopanic-1",
    )

    assert 0 <= confidence <= 1


def test_stronger_score_has_no_lower_confidence_when_other_inputs_match() -> None:
    weak = classification_confidence(
        0.1,
        RelevanceLabel.RELEVANT,
        headline="Bitcoin market update",
        source_id="cryptopanic-1",
    )
    strong = classification_confidence(
        0.8,
        RelevanceLabel.RELEVANT,
        headline="Bitcoin market update",
        source_id="cryptopanic-1",
    )

    assert strong >= weak


def test_relevance_and_source_completeness_affect_confidence() -> None:
    complete_relevant = classification_confidence(
        0.4,
        RelevanceLabel.RELEVANT,
        headline="Bitcoin rally",
        source_id="cryptopanic-1",
    )
    missing_source_noise = classification_confidence(
        0.4,
        RelevanceLabel.NOISE,
        headline="Bitcoin rally",
    )

    assert complete_relevant > missing_source_noise


def test_classification_confidence_is_deterministic() -> None:
    kwargs = {
        "headline": "Bitcoin rally",
        "source_name": "CryptoPanic",
    }

    assert classification_confidence(0.4, RelevanceLabel.RELEVANT, **kwargs) == (
        classification_confidence(0.4, RelevanceLabel.RELEVANT, **kwargs)
    )


def test_confidence_helper_names_classification_not_market_certainty() -> None:
    assert "classification" in classification_confidence.__name__
    assert "market" not in classification_confidence.__name__
