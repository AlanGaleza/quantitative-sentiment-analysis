from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from quantitative_sentiment_analysis.backtest_dataset import (
    MAX_DATASET_PREVIEW_RECORDS,
    DatasetProviderLimitation,
    DatasetRunPreview,
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    Instrument,
    RelevanceLabel,
    RunMode,
)

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
EVENT_TIME = datetime(2026, 6, 2, 9, 30, tzinfo=UTC)


def make_summary(**overrides: object) -> DatasetRunSummary:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-000001",
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
        "status": DatasetRunStatus.COMPLETED,
        "provider_name": "Sharpe Terminal",
        "record_count": 1,
        "relevant_count": 1,
        "noise_count": 0,
        "irrelevant_count": 0,
        "model_version": "sentiment-policy-v1",
        "config_version": "news-policy-v1",
        "input_fingerprint": "fingerprint-alpha",
    }
    payload.update(overrides)
    return DatasetRunSummary.model_validate(payload)


def make_record(**overrides: object) -> DatasetRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-000001",
        "record_id": "sharpe:1",
        "timestamp": EVENT_TIME,
        "headline": "Bitcoin ETF inflows support BTC price",
        "source_id": "sharpe",
        "instrument": Instrument.BTCUSD,
        "mode": RunMode.BACKTEST,
        "sentiment_score": 0.45,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.72,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-policy-v1",
        "config_version": "news-policy-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def test_status_enum_values_are_stable() -> None:
    assert DatasetRunStatus.DRAFT == "DRAFT"
    assert DatasetRunStatus.RUNNING == "RUNNING"
    assert DatasetRunStatus.COMPLETED == "COMPLETED"
    assert DatasetRunStatus.FAILED_PROVIDER_LIMITATION == "FAILED_PROVIDER_LIMITATION"


def test_summary_preserves_btcusd_backtest_identity_and_counts() -> None:
    summary = make_summary()

    assert summary.workspace_id == "workspace-alpha"
    assert summary.run_id == "draft-run-000001"
    assert summary.instrument is Instrument.BTCUSD
    assert summary.mode is RunMode.BACKTEST
    assert summary.record_count == 1
    assert summary.relevant_count == 1
    assert summary.model_version == "sentiment-policy-v1"
    assert summary.config_version == "news-policy-v1"
    assert summary.input_fingerprint == "fingerprint-alpha"


@pytest.mark.parametrize("field", ["timeframe_start", "timeframe_end"])
def test_summary_rejects_naive_timeframe(field: str) -> None:
    with pytest.raises(ValidationError):
        make_summary(**{field: datetime(2026, 6, 1, 12, 0)})


def test_summary_rejects_reversed_timeframe() -> None:
    with pytest.raises(ValidationError, match="timeframe_end"):
        make_summary(timeframe_start=TIMEFRAME_END, timeframe_end=TIMEFRAME_START)


def test_summary_rejects_count_mismatch() -> None:
    with pytest.raises(ValidationError, match="record_count"):
        make_summary(record_count=2, relevant_count=1, noise_count=0, irrelevant_count=0)


def test_provider_limitation_is_required_for_provider_limited_failures() -> None:
    with pytest.raises(ValidationError, match="provider_limitation"):
        make_summary(
            status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
            record_count=0,
            relevant_count=0,
        )

    summary = make_summary(
        status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
        record_count=0,
        relevant_count=0,
        provider_limitation=DatasetProviderLimitation(
            provider_name="Sharpe Terminal",
            reason="missing configuration",
            detail="Set SHARPE_API_KEY for a manual BACKTEST smoke check.",
        ),
    )

    assert summary.provider_limitation is not None
    assert summary.provider_limitation.provider_name == "Sharpe Terminal"
    assert summary.provider_limitation.reason == "missing configuration"


def test_completed_summary_rejects_provider_limitation() -> None:
    with pytest.raises(ValidationError, match="provider_limitation"):
        make_summary(
            provider_limitation=DatasetProviderLimitation(
                provider_name="Sharpe Terminal",
                reason="missing configuration",
            )
        )


def test_preview_reuses_canonical_dataset_records() -> None:
    record = make_record()
    preview = DatasetRunPreview(summary=make_summary(), records=[record])

    assert isinstance(preview.records[0], DatasetRecord)
    assert preview.records == (record,)
    assert preview.records[0].sentiment_score == 0.45
    assert preview.records[0].directional_bias is DirectionalBias.LONG
    assert preview.records[0].confidence == 0.72


def test_preview_rejects_more_than_bounded_record_limit() -> None:
    records = [
        make_record(record_id=f"sharpe:{index}", headline=f"BTC headline {index}")
        for index in range(MAX_DATASET_PREVIEW_RECORDS + 1)
    ]

    with pytest.raises(ValidationError):
        DatasetRunPreview(
            summary=make_summary(
                record_count=len(records),
                relevant_count=len(records),
            ),
            records=records,
        )


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("workspace_id", "workspace-beta", "workspace_id"),
        ("run_id", "other-run", "run_id"),
        ("model_version", "other-model", "model_version"),
        ("config_version", "other-config", "config_version"),
    ],
)
def test_preview_rejects_records_that_do_not_match_summary(
    field: str,
    value: object,
    match: str,
) -> None:
    with pytest.raises(ValidationError, match=match):
        DatasetRunPreview(summary=make_summary(), records=[make_record(**{field: value})])


def test_preview_rejects_more_records_than_summary_count() -> None:
    with pytest.raises(ValidationError, match="record_count"):
        DatasetRunPreview(
            summary=make_summary(record_count=0, relevant_count=0),
            records=[make_record()],
        )


def test_preview_allows_bounded_subset_of_larger_completed_dataset() -> None:
    preview = DatasetRunPreview(
        summary=make_summary(record_count=10, relevant_count=10),
        records=[make_record()],
    )

    assert len(preview.records) == 1
    assert preview.summary.record_count == 10


def test_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        make_summary(unexpected="value")

    with pytest.raises(ValidationError):
        DatasetProviderLimitation(
            provider_name="Sharpe Terminal",
            reason="missing configuration",
            unexpected="value",
        )

    with pytest.raises(ValidationError):
        DatasetRunPreview(summary=make_summary(), records=[make_record()], unexpected="x")
