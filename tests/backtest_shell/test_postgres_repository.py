from __future__ import annotations

from datetime import UTC, datetime

import pytest

from quantitative_sentiment_analysis.backtest_shell.repository import (
    BacktestShellRunNotFoundError,
    PostgresBacktestShellRepository,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import (
    CreateBacktestRunRequest,
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
