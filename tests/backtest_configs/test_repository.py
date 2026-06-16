from __future__ import annotations

from datetime import UTC, datetime

import pytest

from quantitative_sentiment_analysis.backtest_configs.repository import (
    BacktestConfigConflictError,
    BacktestConfigNotFoundError,
    BacktestConfigRepository,
)
from quantitative_sentiment_analysis.backtest_configs.schemas import (
    CreateBacktestConfigRequest,
    UpdateBacktestConfigRequest,
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
UPDATED_START = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
UPDATED_END = datetime(2026, 6, 9, 12, 0, tzinfo=UTC)


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


def create_request(name: str = "Baseline BTC config") -> CreateBacktestConfigRequest:
    return CreateBacktestConfigRequest(
        name=name,
        timeframe_start=TIMEFRAME_START,
        timeframe_end=TIMEFRAME_END,
    )


def test_config_repository_crud_is_scoped_to_workspace(session_factory) -> None:
    with session_factory() as session:
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        seed_user_with_workspace(
            session,
            email="other@example.test",
            workspace_slug="workspace-beta",
            workspace_name="Workspace Beta",
        )
        repository = BacktestConfigRepository(session)

        created = repository.create("workspace-alpha", create_request())

        assert created.workspace_id == "workspace-alpha"
        assert created.name == "Baseline BTC config"
        assert repository.list("workspace-alpha")[0].model_dump() == created.model_dump()
        assert repository.list("workspace-beta") == ()
        assert repository.get("workspace-alpha", created.id) == created
        with pytest.raises(BacktestConfigNotFoundError):
            repository.get("workspace-beta", created.id)

        updated = repository.update(
            "workspace-alpha",
            created.id,
            UpdateBacktestConfigRequest(
                name="Renamed config",
                timeframe_start=UPDATED_START,
                timeframe_end=UPDATED_END,
            ),
        )

        assert updated.name == "Renamed config"
        assert updated.timeframe_start == UPDATED_START
        assert updated.timeframe_end == UPDATED_END

        repository.delete("workspace-alpha", created.id)

        assert repository.list("workspace-alpha") == ()
        with pytest.raises(BacktestConfigNotFoundError):
            repository.get("workspace-alpha", created.id)


def test_config_repository_enforces_unique_name_per_workspace(session_factory) -> None:
    with session_factory() as session:
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        seed_user_with_workspace(
            session,
            email="other@example.test",
            workspace_slug="workspace-beta",
            workspace_name="Workspace Beta",
        )
        repository = BacktestConfigRepository(session)
        repository.create("workspace-alpha", create_request("Shared name"))

        with pytest.raises(BacktestConfigConflictError):
            repository.create("workspace-alpha", create_request("Shared name"))

        other = repository.create("workspace-beta", create_request("Shared name"))

        assert other.workspace_id == "workspace-beta"


def test_config_repository_validates_final_timeframe_on_partial_update(
    session_factory,
) -> None:
    with session_factory() as session:
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        repository = BacktestConfigRepository(session)
        created = repository.create("workspace-alpha", create_request())

        with pytest.raises(ValueError, match="timeframe_end"):
            repository.update(
                "workspace-alpha",
                created.id,
                UpdateBacktestConfigRequest(timeframe_start=UPDATED_END),
            )
