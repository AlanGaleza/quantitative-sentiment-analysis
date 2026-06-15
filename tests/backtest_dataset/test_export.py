from __future__ import annotations

from datetime import UTC, datetime
import json

import pytest

from quantitative_sentiment_analysis.backtest_dataset import (
    DatasetExportNotReadyError,
    DatasetProviderLimitation,
    DatasetRunStatus,
    DatasetRunSummary,
    InMemoryCompletedDatasetRepository,
    export_dataset_jsonl_bytes,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
)

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


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
        "record_id": "cryptopanic:001",
        "timestamp": datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
        "headline": "Bitcoin ETF inflows support BTC price",
        "source_id": "coinwire",
        "source_name": "CoinWire",
        "sentiment_score": 0.45,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.72,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-policy-v1",
        "config_version": "news-policy-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def test_export_jsonl_bytes_are_stable_utf8_records_without_metadata_line() -> None:
    repository = InMemoryCompletedDatasetRepository()
    records = [
        make_record(
            record_id="cryptopanic:002",
            timestamp=datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
            headline="Bitcoin rally extends as zloto demand rises",
            source_id=None,
            source_name="Crypto Desk",
            relevance=RelevanceLabel.NOISE,
            sentiment_score=0.0,
            directional_bias=DirectionalBias.FLAT,
            confidence=0.5,
        ),
        make_record(
            record_id="cryptopanic:001",
            headline="Bitcoin ETF inflows support BTC price - Lodz desk",
        ),
    ]
    repository.save_run(
        make_summary(record_count=2, relevant_count=1, noise_count=1),
        list(reversed(records)),
    )

    first = export_dataset_jsonl_bytes(
        repository,
        "workspace-alpha",
        "draft-run-000001",
    )
    second = export_dataset_jsonl_bytes(
        repository,
        "workspace-alpha",
        "draft-run-000001",
    )

    assert first == second
    decoded = first.decode("utf-8")
    assert decoded.endswith("\n")
    assert "\n\n" not in decoded
    lines = decoded.splitlines()
    assert len(lines) == 2

    payloads = [json.loads(line) for line in lines]
    assert payloads[0]["record_id"] == "cryptopanic:001"
    assert payloads[1]["record_id"] == "cryptopanic:002"
    assert all(payload["workspace_id"] == "workspace-alpha" for payload in payloads)
    assert all(payload["run_id"] == "draft-run-000001" for payload in payloads)
    assert all(payload["config_version"] == "news-policy-v1" for payload in payloads)
    assert payloads[0]["directional_bias"] == "LONG"
    assert payloads[0]["confidence"] == 0.72
    assert payloads[0]["source_id"] == "coinwire"
    assert payloads[0]["source_name"] == "CoinWire"
    assert payloads[1]["relevance"] == "NOISE"
    assert "record_count" not in payloads[0]
    assert "provider_name" not in payloads[0]


def test_export_sort_is_independent_of_repository_order() -> None:
    repository = InMemoryCompletedDatasetRepository()
    records = [
        make_record(
            record_id="record-b",
            timestamp=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
            headline="B headline",
            source_id="source-b",
        ),
        make_record(
            record_id="record-a",
            timestamp=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
            headline="A headline",
            source_id="source-a",
        ),
        make_record(
            record_id=None,
            timestamp=datetime(2026, 6, 1, 9, 0, tzinfo=UTC),
            headline="Earlier headline",
            source_id=None,
            source_name="Earlier Source",
        ),
        make_record(
            record_id="record-c",
            timestamp=datetime(2026, 6, 2, 9, 0, tzinfo=UTC),
            headline="C headline",
            source_id=None,
            source_name="Named Source",
        ),
    ]
    repository.save_run(
        make_summary(record_count=4, relevant_count=4),
        [records[3], records[0], records[2], records[1]],
    )

    body = export_dataset_jsonl_bytes(
        repository,
        "workspace-alpha",
        "draft-run-000001",
    )

    record_ids = [json.loads(line)["record_id"] for line in body.decode().splitlines()]
    assert record_ids == [None, "record-a", "record-b", "record-c"]


def test_export_keeps_all_records_not_only_bounded_preview() -> None:
    repository = InMemoryCompletedDatasetRepository()
    records = [
        make_record(
            record_id=f"cryptopanic:{index:03d}",
            headline=f"Bitcoin dataset export row {index}",
        )
        for index in range(105)
    ]
    repository.save_run(
        make_summary(record_count=105, relevant_count=105),
        records,
    )

    body = export_dataset_jsonl_bytes(
        repository,
        "workspace-alpha",
        "draft-run-000001",
    )

    assert len(body.decode("utf-8").splitlines()) == 105


def test_export_rejects_provider_limited_terminal_run() -> None:
    repository = InMemoryCompletedDatasetRepository()
    repository.save_run(
        make_summary(
            status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
            record_count=0,
            relevant_count=0,
            provider_limitation=DatasetProviderLimitation(
                provider_name="CryptoPanic",
                reason="missing configuration",
                detail="Set CRYPTOPANIC_API_KEY for a manual BACKTEST smoke check.",
            ),
        ),
        [],
    )

    with pytest.raises(DatasetExportNotReadyError, match="COMPLETED"):
        export_dataset_jsonl_bytes(
            repository,
            "workspace-alpha",
            "draft-run-000001",
        )
