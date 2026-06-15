from __future__ import annotations

from datetime import UTC, datetime

from quantitative_sentiment_analysis.contracts import (
    BacktestRunMetadata,
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
    dataset_record_jsonl_line,
    run_fingerprint_material,
    stable_json_data,
    stable_json_dumps,
    stable_run_fingerprint,
)


def make_record(**overrides: object) -> DatasetRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "run-001",
        "record_id": "record-001",
        "timestamp": datetime(2026, 6, 8, 12, 0, tzinfo=UTC),
        "headline": "Bitcoin ETF inflows rise ahead of US session",
        "source_name": "Example Crypto News",
        "sentiment_score": 0.42,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.81,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-rules-v1",
        "config_version": "dataset-config-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def make_metadata(**overrides: object) -> BacktestRunMetadata:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "run-001",
        "timeframe_start": datetime(2026, 6, 1, tzinfo=UTC),
        "timeframe_end": datetime(2026, 6, 8, tzinfo=UTC),
        "seed": 42,
        "model_version": "sentiment-rules-v1",
        "config_version": "dataset-config-v1",
        "input_fingerprint": "news-input-sha256",
    }
    payload.update(overrides)
    return BacktestRunMetadata.model_validate(payload)


def test_stable_json_data_normalizes_models_enums_and_datetimes() -> None:
    data = stable_json_data(make_record())

    assert data["timestamp"] == "2026-06-08T12:00:00Z"
    assert data["directional_bias"] == "LONG"
    assert data["relevance"] == "RELEVANT"


def test_stable_json_dumps_is_key_order_stable() -> None:
    first = stable_json_dumps({"b": 2, "a": {"d": 4, "c": 3}})
    second = stable_json_dumps({"a": {"c": 3, "d": 4}, "b": 2})

    assert first == second
    assert first == '{"a":{"c":3,"d":4},"b":2}'


def test_dataset_record_jsonl_line_is_byte_stable() -> None:
    record = make_record()

    first = dataset_record_jsonl_line(record)
    second = dataset_record_jsonl_line(make_record())

    assert first == second
    assert first.endswith("\n")
    assert "\n" not in first[:-1]
    assert '"timestamp":"2026-06-08T12:00:00Z"' in first
    assert '"directional_bias":"LONG"' in first


def test_run_fingerprint_material_excludes_run_id() -> None:
    material = run_fingerprint_material(make_metadata(run_id="run-a"))

    assert "run_id" not in material
    assert material["workspace_id"] == "workspace-alpha"
    assert material["seed"] == 42


def test_run_fingerprint_is_stable_for_same_determinism_inputs() -> None:
    first = stable_run_fingerprint(make_metadata(run_id="run-a"))
    second = stable_run_fingerprint(make_metadata(run_id="run-b"))

    assert first == second


def test_run_fingerprint_changes_when_determinism_inputs_change() -> None:
    baseline = stable_run_fingerprint(make_metadata())

    assert stable_run_fingerprint(make_metadata(seed=43)) != baseline
    assert stable_run_fingerprint(make_metadata(model_version="sentiment-rules-v2")) != baseline
    assert stable_run_fingerprint(make_metadata(config_version="dataset-config-v2")) != baseline
    assert stable_run_fingerprint(make_metadata(input_fingerprint="other-input")) != baseline
    assert stable_run_fingerprint(
        make_metadata(timeframe_end=datetime(2026, 6, 9, tzinfo=UTC))
    ) != baseline
