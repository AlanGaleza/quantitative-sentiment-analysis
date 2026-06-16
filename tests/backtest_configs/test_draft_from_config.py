from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from quantitative_sentiment_analysis.main import create_app
from quantitative_sentiment_analysis.persistence.database import (
    create_session_factory,
    reset_database_state_for_tests,
)
from quantitative_sentiment_analysis.persistence.models import BacktestRunModel
from tests.postgres_helpers import (
    FRONTEND_ORIGIN,
    clear_database,
    login,
    override_database_session,
    postgres_engine_or_skip,
    seed_user_with_workspace,
)

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


@pytest.fixture()
def client_and_session_factory(monkeypatch: pytest.MonkeyPatch):
    engine = postgres_engine_or_skip(monkeypatch)
    session_factory = create_session_factory(engine)
    test_app = create_app(cors_allowed_origins=[FRONTEND_ORIGIN])
    override_database_session(test_app, engine)
    with session_factory() as session:
        clear_database(session)
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
    with TestClient(test_app, base_url="https://api.example.test") as client:
        yield client, session_factory
    with session_factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()


def config_payload() -> dict[str, object]:
    return {
        "name": "Draft source config",
        "instrument": "BTCUSD",
        "mode": "BACKTEST",
        "timeframe_start": TIMEFRAME_START.isoformat(),
        "timeframe_end": TIMEFRAME_END.isoformat(),
    }


def test_draft_from_config_creates_normal_durable_draft_run(
    client_and_session_factory,
) -> None:
    client, session_factory = client_and_session_factory
    login(client)
    create_response = client.post(
        "/api/workspaces/workspace-alpha/backtest-configs",
        json=config_payload(),
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert create_response.status_code == 200
    config_id = create_response.json()["id"]

    draft_response = client.post(
        f"/api/workspaces/workspace-alpha/backtest-configs/{config_id}/drafts",
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["workspace_id"] == "workspace-alpha"
    assert draft["instrument"] == "BTCUSD"
    assert draft["mode"] == "BACKTEST"
    assert draft["status"] == "DRAFT"

    get_response = client.get(
        f"/api/workspaces/workspace-alpha/backtests/{draft['run_id']}"
    )
    assert get_response.status_code == 200
    assert get_response.json() == draft

    with session_factory() as session:
        stored_run = session.scalar(
            select(BacktestRunModel).where(BacktestRunModel.run_id == draft["run_id"])
        )
        assert stored_run is not None
        assert str(stored_run.config_id) == config_id


def test_deleting_config_keeps_already_created_draft_run(
    client_and_session_factory,
) -> None:
    client, session_factory = client_and_session_factory
    login(client)
    create_response = client.post(
        "/api/workspaces/workspace-alpha/backtest-configs",
        json=config_payload(),
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert create_response.status_code == 200
    config_id = create_response.json()["id"]
    draft_response = client.post(
        f"/api/workspaces/workspace-alpha/backtest-configs/{config_id}/drafts",
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert draft_response.status_code == 200
    run_id = draft_response.json()["run_id"]

    delete_response = client.delete(
        f"/api/workspaces/workspace-alpha/backtest-configs/{config_id}",
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert delete_response.status_code == 204

    run_response = client.get(f"/api/workspaces/workspace-alpha/backtests/{run_id}")
    assert run_response.status_code == 200

    with session_factory() as session:
        stored_run = session.scalar(
            select(BacktestRunModel).where(BacktestRunModel.run_id == run_id)
        )
        assert stored_run is not None
        assert stored_run.config_id is None


def test_draft_from_config_returns_404_for_missing_config(
    client_and_session_factory,
) -> None:
    client, _session_factory = client_and_session_factory
    login(client)

    response = client.post(
        "/api/workspaces/workspace-alpha/backtest-configs/"
        "00000000-0000-0000-0000-000000000000/drafts",
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert response.status_code == 404
