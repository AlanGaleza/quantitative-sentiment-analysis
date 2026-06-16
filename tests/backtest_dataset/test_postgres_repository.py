from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quantitative_sentiment_analysis.backtest_dataset.export import (
    DatasetExportNotReadyError,
    export_dataset_jsonl_bytes,
)
from quantitative_sentiment_analysis.backtest_dataset.repository import (
    CompletedDatasetRunNotFoundError,
    PostgresCompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetProviderLimitation,
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.backtest_shell.repository import (
    PostgresBacktestShellRepository,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import (
    CreateBacktestRunRequest,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.persistence.database import (
    create_session_factory,
    reset_database_state_for_tests,
)
from tests.postgres_helpers import (
    clear_database,
    postgres_engine_or_skip,
    seed_user_with_workspace,
)

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)
EVENT_TIME = datetime(2026, 6, 2, 9, 30, tzinfo=UTC)


@pytest.fixture()
def session_factory(monkeypatch: pytest.MonkeyPatch):
    engine = postgres_engine_or_skip(monkeypatch)
    factory = create_session_factory(engine)
    with factory() as session:
        clear_database(session)
    yield factory
    with factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()


def draft_request() -> CreateBacktestRunRequest:
    return CreateBacktestRunRequest(
        timeframe_start=TIMEFRAME_START,
        timeframe_end=TIMEFRAME_END,
    )


def create_draft(session) -> None:
    seed_user_with_workspace(session, workspace_slug="workspace-alpha")
    PostgresBacktestShellRepository(
        session,
        run_id_factory=lambda workspace_id, request: "draft-run-fixed",
        clock=lambda: CREATED_AT,
    ).create_draft_run("workspace-alpha", draft_request())


def make_summary(**overrides: object) -> DatasetRunSummary:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-fixed",
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
        "status": DatasetRunStatus.COMPLETED,
        "provider_name": "FixtureNews",
        "record_count": 2,
        "relevant_count": 1,
        "noise_count": 1,
        "irrelevant_count": 0,
        "model_version": "sentiment-rules-v1",
        "config_version": "news-sentiment-policy-v1",
        "input_fingerprint": "fingerprint-alpha",
    }
    payload.update(overrides)
    return DatasetRunSummary.model_validate(payload)


def make_record(index: int, **overrides: object) -> DatasetRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-fixed",
        "record_id": f"record-{index:03d}",
        "timestamp": EVENT_TIME + timedelta(minutes=index),
        "headline": f"Bitcoin ETF approval headline {index}",
        "source_name": "FixtureNews",
        "sentiment_score": 0.45,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.72,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-rules-v1",
        "config_version": "news-sentiment-policy-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def test_postgres_dataset_repository_persists_summary_preview_and_full_records(
    session_factory,
) -> None:
    with session_factory() as session:
        create_draft(session)
        repository = PostgresCompletedDatasetRepository(session)
        records = [
            make_record(2, relevance=RelevanceLabel.NOISE, sentiment_score=0.0),
            make_record(1),
        ]

        preview = repository.save_run(make_summary(), records)

        assert preview.summary.workspace_id == "workspace-alpha"
        assert preview.summary.record_count == 2
        assert [record.record_id for record in preview.records] == [
            "record-001",
            "record-002",
        ]

    with session_factory() as session:
        repository = PostgresCompletedDatasetRepository(session)
        persisted = repository.get_run("workspace-alpha", "draft-run-fixed")
        full_records = repository.list_records("workspace-alpha", "draft-run-fixed")

    assert persisted.summary == preview.summary
    assert tuple(record.record_id for record in full_records) == (
        "record-001",
        "record-002",
    )


def test_postgres_dataset_repository_stores_provider_limited_terminal_runs(
    session_factory,
) -> None:
    with session_factory() as session:
        create_draft(session)
        repository = PostgresCompletedDatasetRepository(session)
        summary = make_summary(
            status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
            record_count=0,
            relevant_count=0,
            noise_count=0,
            provider_limitation=DatasetProviderLimitation(
                provider_name="Sharpe Terminal",
                reason="missing provider configuration",
                detail="Set SHARPE_API_KEY locally for a BACKTEST smoke check.",
            ),
        )

        preview = repository.save_run(summary, [])

        assert preview.summary.status is DatasetRunStatus.FAILED_PROVIDER_LIMITATION
        assert preview.summary.provider_limitation is not None
        assert preview.records == ()
        assert repository.list_records("workspace-alpha", "draft-run-fixed") == ()
        with pytest.raises(DatasetExportNotReadyError):
            export_dataset_jsonl_bytes(repository, "workspace-alpha", "draft-run-fixed")


def test_postgres_dataset_repository_requires_existing_workspace_run(
    session_factory,
) -> None:
    with session_factory() as session:
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        repository = PostgresCompletedDatasetRepository(session)

        with pytest.raises(CompletedDatasetRunNotFoundError):
            repository.save_run(
                make_summary(),
                [
                    make_record(1),
                    make_record(
                        2,
                        relevance=RelevanceLabel.NOISE,
                        sentiment_score=0.0,
                    ),
                ],
            )


def test_postgres_dataset_jsonl_export_is_stable_across_sessions(session_factory) -> None:
    with session_factory() as session:
        create_draft(session)
        repository = PostgresCompletedDatasetRepository(session)
        repository.save_run(
            make_summary(record_count=3, relevant_count=2, noise_count=1),
            [
                make_record(3),
                make_record(1),
                make_record(2, relevance=RelevanceLabel.NOISE, sentiment_score=0.0),
            ],
        )
        first_body = export_dataset_jsonl_bytes(
            repository,
            "workspace-alpha",
            "draft-run-fixed",
        )

    with session_factory() as session:
        second_body = export_dataset_jsonl_bytes(
            PostgresCompletedDatasetRepository(session),
            "workspace-alpha",
            "draft-run-fixed",
        )

    assert first_body == second_body
    assert first_body.decode("utf-8").splitlines()[0].find("record-001") > -1
