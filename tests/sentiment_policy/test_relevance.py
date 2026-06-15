from quantitative_sentiment_analysis.contracts.schemas import RelevanceLabel
from quantitative_sentiment_analysis.sentiment_policy import relevance_for_text


def test_relevance_labels_btc_records_as_relevant() -> None:
    assert (
        relevance_for_text(
            "Bitcoin rally lifts BTCUSD after ETF approval",
            source_id="sharpe-1",
        )
        is RelevanceLabel.RELEVANT
    )


def test_relevance_labels_non_btc_crypto_records_as_irrelevant_not_filtered() -> None:
    label = relevance_for_text(
        "Ethereum upgrade draws crypto developer attention",
        source_id="sharpe-2",
    )

    assert label is RelevanceLabel.IRRELEVANT


def test_relevance_labels_noise_records_without_removing_them() -> None:
    label = relevance_for_text("Sponsored promo placeholder", source_name="Sharpe Terminal")

    assert label is RelevanceLabel.NOISE


def test_relevance_labels_missing_source_identity_as_noise_for_audit() -> None:
    label = relevance_for_text("Bitcoin rally lifts BTCUSD")

    assert label is RelevanceLabel.NOISE
