from __future__ import annotations

from datetime import UTC, datetime
import uuid

import pytest
from sqlalchemy import select

from quantitative_sentiment_analysis.backtest_configs.repository import (
    BacktestConfigRepository,
)
from quantitative_sentiment_analysis.backtest_configs.schemas import (
    CreateBacktestConfigRequest,
)
from quantitative_sentiment_analysis.backtest_dataset.repository import (
    PostgresCompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetProviderLimitation,
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.backtest_shell.repository import (
    BacktestShellRunNotFoundError,
    PostgresBacktestShellRepository,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import (
    BacktestDatasetRunStatus,
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
from quantitative_sentiment_analysis.persistence.models import BacktestRunModel
from tests.postgres_helpers import (
    clear_database,
    postgres_engine_or_skip,
    seed_user_with_workspace,
)

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)
LATER_CREATED_AT = datetime(2026, 6, 8, 13, 30, tzinfo=UTC)
LATEST_CREATED_AT = datetime(2026, 6, 8, 14, 30, tzinfo=UTC)
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


def config_request(name: str) -> CreateBacktestConfigRequest:
    return CreateBacktestConfigRequest(
        name=name,
        timeframe_start=TIMEFRAME_START,
        timeframe_end=TIMEFRAME_END,
    )


def dataset_summary(run_id: str, **overrides: object) -> DatasetRunSummary:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": run_id,
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
        "status": DatasetRunStatus.COMPLETED,
        "provider_name": "Sharpe Terminal",
        "record_count": 1,
        "relevant_count": 1,
        "noise_count": 0,
        "irrelevant_count": 0,
        "model_version": "sentiment-rules-v1",
        "config_version": "news-sentiment-policy-v1",
        "input_fingerprint": f"fingerprint-{run_id}",
    }
    payload.update(overrides)
    return DatasetRunSummary.model_validate(payload)


def dataset_record(run_id: str) -> DatasetRecord:
    return DatasetRecord(
        workspace_id="workspace-alpha",
        run_id=run_id,
        record_id=f"{run_id}:record-001",
        timestamp=EVENT_TIME,
        headline="Bitcoin ETF approval sparks bullish inflows",
        source_name="Sharpe Terminal",
        sentiment_score=0.75,
        directional_bias=DirectionalBias.LONG,
        confidence=0.8,
        relevance=RelevanceLabel.RELEVANT,
        model_version="sentiment-rules-v1",
        config_version="news-sentiment-policy-v1",
    )


def create_fixed_run(
    session,
    *,
    workspace_id: str,
    run_id: str,
    created_at: datetime,
    config_id: uuid.UUID | None = None,
) -> None:
    repository = PostgresBacktestShellRepository(
        session,
        run_id_factory=lambda _workspace_id, _request: run_id,
        clock=lambda: created_at,
    )
    if config_id is None:
        repository.create_draft_run(workspace_id, draft_request())
        return
    repository.create_draft_run_from_config(
        workspace_id=workspace_id,
        config_id=config_id,
        request=draft_request(),
    )


def test_postgres_shell_repository_creates_and_reads_workspace_scoped_run(
    session_factory,
) -> None:
    with session_factory() as session:
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        repository = PostgresBacktestShellRepository(
            session,
            run_id_factory=lambda workspace_id, request: "draft-run-fixed",
            clock=lambda: CREATED_AT,
        )

        created = repository.create_draft_run("workspace-alpha", draft_request())

        assert created.workspace_id == "workspace-alpha"
        assert created.run_id == "draft-run-fixed"
        assert created.created_at == CREATED_AT
        assert created.quality_report_path == (
            "/workspaces/workspace-alpha/backtests/draft-run-fixed/quality"
        )

    with session_factory() as session:
        persisted = PostgresBacktestShellRepository(session).get_run(
            "workspace-alpha",
            "draft-run-fixed",
        )

    assert persisted == created


def test_postgres_shell_repository_enforces_workspace_boundary(session_factory) -> None:
    with session_factory() as session:
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        seed_user_with_workspace(
            session,
            email="other@example.test",
            workspace_slug="workspace-beta",
            workspace_name="Workspace Beta",
        )
        repository = PostgresBacktestShellRepository(
            session,
            run_id_factory=lambda workspace_id, request: "draft-run-fixed",
            clock=lambda: CREATED_AT,
        )
        repository.create_draft_run("workspace-alpha", draft_request())

        with pytest.raises(BacktestShellRunNotFoundError):
            repository.get_run("workspace-beta", "draft-run-fixed")

        with pytest.raises(BacktestShellRunNotFoundError):
            repository.create_draft_run("missing-workspace", draft_request())


def test_postgres_shell_repository_lists_workspace_run_history(session_factory) -> None:
    with session_factory() as session:
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        config = BacktestConfigRepository(session).create(
            "workspace-alpha",
            config_request("Config One"),
        )
        config_uuid = uuid.UUID(config.id)

        create_fixed_run(
            session,
            workspace_id="workspace-alpha",
            run_id="draft-run-000001",
            created_at=CREATED_AT,
        )
        create_fixed_run(
            session,
            workspace_id="workspace-alpha",
            run_id="draft-run-000002",
            created_at=LATER_CREATED_AT,
            config_id=config_uuid,
        )
        create_fixed_run(
            session,
            workspace_id="workspace-alpha",
            run_id="draft-run-000003",
            created_at=LATEST_CREATED_AT,
            config_id=config_uuid,
        )
        dataset_repository = PostgresCompletedDatasetRepository(session)
        dataset_repository.save_run(
            dataset_summary("draft-run-000002"),
            [dataset_record("draft-run-000002")],
        )
        dataset_repository.save_run(
            dataset_summary(
                "draft-run-000003",
                status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
                record_count=0,
                relevant_count=0,
                provider_limitation=DatasetProviderLimitation(
                    provider_name="Sharpe Terminal",
                    reason="missing provider configuration",
                    detail="Set SHARPE_API_KEY locally for a BACKTEST smoke check.",
                ),
            ),
            [],
        )

        history = PostgresBacktestShellRepository(session).list_runs("workspace-alpha")

    assert history.workspace_id == "workspace-alpha"
    assert [run.run_id for run in history.runs] == [
        "draft-run-000003",
        "draft-run-000002",
        "draft-run-000001",
    ]

    provider_limited = history.runs[0]
    assert provider_limited.config_id == config.id
    assert provider_limited.config_name == "Config One"
    assert (
        provider_limited.dataset_status
        is BacktestDatasetRunStatus.FAILED_PROVIDER_LIMITATION
    )
    assert provider_limited.provider_limitation is not None
    assert (
        provider_limited.provider_limitation.reason == "missing provider configuration"
    )
    assert provider_limited.dataset_preview_path == (
        "/api/workspaces/workspace-alpha/backtests/draft-run-000003/dataset"
    )
    assert provider_limited.dataset_export_path is None
    assert provider_limited.quality_report_path is None

    completed = history.runs[1]
    assert completed.dataset_status is BacktestDatasetRunStatus.COMPLETED
    assert completed.provider_name == "Sharpe Terminal"
    assert completed.record_count == 1
    assert completed.relevant_count == 1
    assert completed.noise_count == 0
    assert completed.irrelevant_count == 0
    assert completed.model_version == "sentiment-rules-v1"
    assert completed.config_version == "news-sentiment-policy-v1"
    assert completed.input_fingerprint == "fingerprint-draft-run-000002"
    assert completed.dataset_preview_path == (
        "/api/workspaces/workspace-alpha/backtests/draft-run-000002/dataset"
    )
    assert completed.dataset_export_path == (
        "/api/workspaces/workspace-alpha/backtests/"
        "draft-run-000002/dataset/export.jsonl"
    )
    assert completed.quality_report_path == (
        "/workspaces/workspace-alpha/backtests/draft-run-000002/quality"
    )

    draft = history.runs[2]
    assert draft.config_id is None
    assert draft.config_name is None
    assert draft.dataset_status is None
    assert draft.dataset_preview_path is None
    assert draft.dataset_export_path is None
    assert draft.quality_report_path is None


def test_postgres_shell_repository_history_enforces_workspace_boundary(
    session_factory,
) -> None:
    with session_factory() as session:
        _alpha_user, alpha_workspace = seed_user_with_workspace(
            session, workspace_slug="workspace-alpha"
        )
        seed_user_with_workspace(
            session,
            email="other@example.test",
            workspace_slug="workspace-beta",
            workspace_name="Workspace Beta",
        )
        beta_config = BacktestConfigRepository(session).create(
            "workspace-beta",
            config_request("Beta Config"),
        )
        create_fixed_run(
            session,
            workspace_id="workspace-alpha",
            run_id="shared-run-id",
            created_at=CREATED_AT,
        )
        alpha_run = session.scalar(
            select(BacktestRunModel).where(
                BacktestRunModel.workspace_id == alpha_workspace.id,
                BacktestRunModel.run_id == "shared-run-id",
            )
        )
        assert alpha_run is not None
        alpha_run.config_id = uuid.UUID(beta_config.id)
        session.commit()
        create_fixed_run(
            session,
            workspace_id="workspace-beta",
            run_id="shared-run-id",
            created_at=LATER_CREATED_AT,
        )

        alpha_history = PostgresBacktestShellRepository(session).list_runs(
            "workspace-alpha"
        )
        beta_history = PostgresBacktestShellRepository(session).list_runs(
            "workspace-beta"
        )

        with pytest.raises(BacktestShellRunNotFoundError):
            PostgresBacktestShellRepository(session).list_runs("missing-workspace")

    assert [run.workspace_id for run in alpha_history.runs] == ["workspace-alpha"]
    assert [run.workspace_id for run in beta_history.runs] == ["workspace-beta"]
    assert alpha_history.runs[0].run_id == "shared-run-id"
    assert alpha_history.runs[0].config_name is None
    assert beta_history.runs[0].run_id == "shared-run-id"
