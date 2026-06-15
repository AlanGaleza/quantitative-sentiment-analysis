from __future__ import annotations

from datetime import UTC, datetime

import pytest
from quantitative_sentiment_analysis.backtest_dataset.normalization import (
    ProviderNormalizationError,
    normalize_provider_records,
)


def test_normalization_sorts_output_stably_for_reordered_provider_input() -> None:
    first_order = [
        {
            "id": "b",
            "published_at": "2026-06-02T10:00:00Z",
            "title": "BTC rally extends after ETF inflows",
            "source": {"id": "coinwire", "title": "CoinWire"},
        },
        {
            "id": "a",
            "published_at": "2026-06-01T10:00:00Z",
            "title": "Bitcoin ETF approval supports sentiment",
            "source": {"id": "cryptodesk", "title": "CryptoDesk"},
        },
    ]
    second_order = list(reversed(first_order))

    normalized_first = normalize_provider_records(
        provider_name="Sharpe Terminal",
        raw_records=first_order,
    )
    normalized_second = normalize_provider_records(
        provider_name="Sharpe Terminal",
        raw_records=second_order,
    )

    assert [record.provider_record_id for record in normalized_first] == ["a", "b"]
    assert [
        record.model_dump(exclude={"original_index"}) for record in normalized_first
    ] == [record.model_dump(exclude={"original_index"}) for record in normalized_second]


def test_normalization_dedupes_only_exact_repeated_provider_ids() -> None:
    normalized = normalize_provider_records(
        provider_name="Sharpe Terminal",
        raw_records=[
            {
                "id": "same-id",
                "published_at": "2026-06-01T10:00:00Z",
                "title": "BTC rally extends",
                "source_name": "Sharpe Terminal",
            },
            {
                "id": "same-id",
                "published_at": "2026-06-01T10:05:00Z",
                "title": "BTC rally extends with more detail",
                "source_name": "Sharpe Terminal",
            },
            {
                "published_at": "2026-06-01T10:10:00Z",
                "title": "BTC rally extends",
                "source_name": "Sharpe Terminal",
            },
            {
                "published_at": "2026-06-01T10:11:00Z",
                "title": "BTC rally extends",
                "source_name": "Sharpe Terminal",
            },
        ],
    )

    assert [record.provider_record_id for record in normalized] == [
        "same-id",
        None,
        None,
    ]
    assert [record.headline for record in normalized] == [
        "BTC rally extends",
        "BTC rally extends",
        "BTC rally extends",
    ]


def test_normalization_preserves_source_identity_and_optional_body() -> None:
    normalized = normalize_provider_records(
        provider_name="Sharpe Terminal",
        raw_records=[
            {
                "id": 123,
                "published_at": datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
                "title": "  Bitcoin   ETF approval   ",
                "summary": " Institutional inflows rise ",
                "source": {"id": "source-1", "name": "Crypto Desk"},
            }
        ],
    )

    record = normalized[0]
    assert record.provider_name == "Sharpe Terminal"
    assert record.provider_record_id == "123"
    assert record.timestamp == datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    assert record.headline == "Bitcoin ETF approval"
    assert record.body == "Institutional inflows rise"
    assert record.source_id == "source-1"
    assert record.source_name == "Crypto Desk"


def test_normalization_preserves_missing_source_identity_for_later_noise_labeling() -> None:
    normalized = normalize_provider_records(
        provider_name="Sharpe Terminal",
        raw_records=[
            {
                "id": "missing-source",
                "published_at": "2026-06-01T10:00:00+00:00",
                "title": "Bitcoin placeholder update",
            }
        ],
    )

    assert normalized[0].source_id is None
    assert normalized[0].source_name is None


def test_normalization_rejects_naive_timestamp() -> None:
    with pytest.raises(ProviderNormalizationError, match="timezone"):
        normalize_provider_records(
            provider_name="Sharpe Terminal",
            raw_records=[
                {
                    "id": "naive",
                    "published_at": datetime(2026, 6, 1, 10, 0),
                    "title": "Bitcoin ETF approval",
                }
            ],
        )


def test_normalization_rejects_missing_timestamp_or_headline() -> None:
    with pytest.raises(ProviderNormalizationError, match="timestamp"):
        normalize_provider_records(
            provider_name="Sharpe Terminal",
            raw_records=[{"id": "missing-timestamp", "title": "Bitcoin ETF approval"}],
        )

    with pytest.raises(ProviderNormalizationError, match="headline"):
        normalize_provider_records(
            provider_name="Sharpe Terminal",
            raw_records=[
                {
                    "id": "missing-headline",
                    "published_at": "2026-06-01T10:00:00Z",
                }
            ],
        )
