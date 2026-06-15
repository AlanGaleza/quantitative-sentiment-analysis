from __future__ import annotations

from datetime import UTC, datetime

import pytest

from quantitative_sentiment_analysis.backtest_dataset import (
    CompletedDatasetRunIncompleteError,
    CompletedDatasetRunNotFoundError,
    DatasetProviderLimitation,
    DatasetRunStatus,
    DatasetRunSummary,
    InMemoryCompletedDatasetRepository,
    MAX_DATASET_PREVIEW_RECORDS,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
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
        "provider_name": "CryptoPanic",
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
        "record_id": "cryptopanic:1",
        "timestamp": EVENT_TIME,
        "headline": "Bitcoin ETF inflows support BTC price",
        "source_name": "CryptoPanic",
        "sentiment_score": 0.45,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.72,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-policy-v1",
        "config_version": "news-policy-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def make_records(count: int) -> list[DatasetRecord]:
    return [
        make_record(
            record_id=f"cryptopanic:{index:03d}",
            headline=f"Bitcoin dataset repository row {index}",
        )
        for index in range(count)
    ]


def test_repository_saves_and_reads_completed_run_by_workspace_and_run() -> None:
    repository = InMemoryCompletedDatasetRepository()
    summary = make_summary()
    record = make_record()

    saved = repository.save_run(summary, [record])

    assert saved.summary == summary
    assert saved.records == (record,)
    assert repository.list_records("workspace-alpha", "draft-run-000001") == (record,)
    assert repository.get_run("workspace-alpha", "draft-run-000001") == saved


def test_repository_reads_are_isolated_by_workspace_and_run_id() -> None:
    repository = InMemoryCompletedDatasetRepository()
    alpha = repository.save_run(make_summary(), [make_record()])
    beta = repository.save_run(
        make_summary(
            workspace_id="workspace-beta",
            run_id="draft-run-000001",
            input_fingerprint="fingerprint-beta",
        ),
        [
            make_record(
                workspace_id="workspace-beta",
                run_id="draft-run-000001",
                record_id="cryptopanic:beta",
            )
        ],
    )

    assert repository.get_run("workspace-alpha", "draft-run-000001") == alpha
    assert repository.get_run("workspace-beta", "draft-run-000001") == beta

    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.get_run("workspace-gamma", "draft-run-000001")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("workspace_id", "workspace-beta", "workspace_id"),
        ("run_id", "draft-run-beta", "run_id"),
    ],
)
def test_repository_rejects_full_record_identity_mismatch_outside_preview(
    field: str,
    value: str,
    match: str,
) -> None:
    repository = InMemoryCompletedDatasetRepository()
    records = make_records(MAX_DATASET_PREVIEW_RECORDS + 1)
    records[-1] = make_record(
        record_id="cryptopanic:mismatch",
        headline="Bitcoin mismatched record outside preview",
        **{field: value},
    )

    with pytest.raises(ValueError, match=match):
        repository.save_run(
            make_summary(record_count=len(records), relevant_count=len(records)),
            records,
        )

    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.get_run("workspace-alpha", "draft-run-000001")
    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.list_records("workspace-alpha", "draft-run-000001")


def test_repository_rejects_full_record_count_mismatch_outside_preview() -> None:
    repository = InMemoryCompletedDatasetRepository()
    records = make_records(MAX_DATASET_PREVIEW_RECORDS + 1)

    with pytest.raises(ValueError, match="record_count"):
        repository.save_run(
            make_summary(record_count=len(records) + 1, relevant_count=len(records) + 1),
            records,
        )

    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.get_run("workspace-alpha", "draft-run-000001")
    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.list_records("workspace-alpha", "draft-run-000001")


def test_repository_rejects_full_relevance_count_mismatch_outside_preview() -> None:
    repository = InMemoryCompletedDatasetRepository()
    records = make_records(MAX_DATASET_PREVIEW_RECORDS + 1)
    records[-1] = make_record(
        record_id="cryptopanic:noise-outside-preview",
        headline="Daily market newsletter roundup",
        relevance=RelevanceLabel.NOISE,
        sentiment_score=0.0,
        directional_bias=DirectionalBias.FLAT,
        confidence=0.5,
    )

    with pytest.raises(ValueError, match="relevant_count"):
        repository.save_run(
            make_summary(record_count=len(records), relevant_count=len(records)),
            records,
        )

    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.get_run("workspace-alpha", "draft-run-000001")
    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.list_records("workspace-alpha", "draft-run-000001")


def test_repository_not_found_error_names_local_non_production_storage() -> None:
    repository = InMemoryCompletedDatasetRepository()

    with pytest.raises(CompletedDatasetRunNotFoundError) as exc_info:
        repository.get_run("workspace-alpha", "missing-run")

    message = str(exc_info.value)
    assert "local/dev" in message
    assert "in-memory" in message
    assert "non-production" in message
    assert "workspace-alpha" in message
    assert "missing-run" in message
    assert "non-production" in repository.storage_description


def test_repository_stores_preview_defensively_against_input_list_mutation() -> None:
    repository = InMemoryCompletedDatasetRepository()
    records = [make_record()]

    saved = repository.save_run(make_summary(), records)
    records.clear()

    assert saved.records == (make_record(),)
    assert repository.get_run("workspace-alpha", "draft-run-000001").records == (
        make_record(),
    )
    assert repository.list_records("workspace-alpha", "draft-run-000001") == (
        make_record(),
    )


def test_repository_accepts_provider_limited_terminal_state_with_no_records() -> None:
    repository = InMemoryCompletedDatasetRepository()
    summary = make_summary(
        status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
        record_count=0,
        relevant_count=0,
        provider_limitation=DatasetProviderLimitation(
            provider_name="CryptoPanic",
            reason="missing configuration",
            detail="Set CRYPTOPANIC_API_KEY for a manual BACKTEST smoke check.",
        ),
    )

    saved = repository.save_run(summary, [])

    assert saved.summary.status is DatasetRunStatus.FAILED_PROVIDER_LIMITATION
    assert saved.summary.provider_limitation is not None
    assert saved.records == ()


def test_repository_rejects_provider_limited_terminal_state_with_records() -> None:
    repository = InMemoryCompletedDatasetRepository()
    summary = make_summary(
        status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
        provider_limitation=DatasetProviderLimitation(
            provider_name="CryptoPanic",
            reason="provider unavailable",
            detail="Temporary provider outage.",
        ),
    )

    with pytest.raises(ValueError, match="provider-limited"):
        repository.save_run(summary, [make_record()])

    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.get_run("workspace-alpha", "draft-run-000001")
    with pytest.raises(CompletedDatasetRunNotFoundError):
        repository.list_records("workspace-alpha", "draft-run-000001")


@pytest.mark.parametrize(
    "status",
    [DatasetRunStatus.DRAFT, DatasetRunStatus.RUNNING],
)
def test_repository_rejects_incomplete_states(status: DatasetRunStatus) -> None:
    repository = InMemoryCompletedDatasetRepository()

    with pytest.raises(CompletedDatasetRunIncompleteError, match="terminal"):
        repository.save_run(
            make_summary(status=status),
            [make_record()],
        )
