from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.main import create_app
from quantitative_sentiment_analysis.persistence.database import (
    create_session_factory,
    reset_database_state_for_tests,
)
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
        seed_user_with_workspace(
            session,
            email="other@example.test",
            workspace_slug="workspace-beta",
            workspace_name="Workspace Beta",
        )
    with TestClient(test_app, base_url="https://api.example.test") as client:
        yield client, session_factory
    with session_factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()


def config_payload(name: str = "Baseline BTC config") -> dict[str, object]:
    return {
        "name": name,
        "instrument": "BTCUSD",
        "mode": "BACKTEST",
        "timeframe_start": TIMEFRAME_START.isoformat(),
        "timeframe_end": TIMEFRAME_END.isoformat(),
    }


def test_config_routes_require_authenticated_session(client_and_session_factory) -> None:
    client, _session_factory = client_and_session_factory

    response = client.get("/api/workspaces/workspace-alpha/backtest-configs")

    assert response.status_code == 401


def test_config_routes_create_list_get_update_and_delete_for_owner(
    client_and_session_factory,
) -> None:
    client, _session_factory = client_and_session_factory
    login(client)

    create_response = client.post(
        "/api/workspaces/workspace-alpha/backtest-configs",
        json=config_payload(),
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["workspace_id"] == "workspace-alpha"
    assert created["name"] == "Baseline BTC config"

    list_response = client.get("/api/workspaces/workspace-alpha/backtest-configs")
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.json()] == [created["id"]]

    get_response = client.get(
        f"/api/workspaces/workspace-alpha/backtest-configs/{created['id']}"
    )
    assert get_response.status_code == 200
    assert get_response.json() == created

    update_response = client.put(
        f"/api/workspaces/workspace-alpha/backtest-configs/{created['id']}",
        json={"name": "Renamed config"},
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Renamed config"

    delete_response = client.delete(
        f"/api/workspaces/workspace-alpha/backtest-configs/{created['id']}",
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    missing_response = client.get(
        f"/api/workspaces/workspace-alpha/backtest-configs/{created['id']}"
    )
    assert missing_response.status_code == 404


def test_config_routes_return_404_for_cross_workspace_access(
    client_and_session_factory,
) -> None:
    client, _session_factory = client_and_session_factory
    login(client)
    create_response = client.post(
        "/api/workspaces/workspace-alpha/backtest-configs",
        json=config_payload(),
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert create_response.status_code == 200
    config_id = create_response.json()["id"]

    response = client.get(
        f"/api/workspaces/workspace-beta/backtest-configs/{config_id}"
    )

    assert response.status_code == 404


def test_config_routes_return_409_for_duplicate_workspace_name(
    client_and_session_factory,
) -> None:
    client, _session_factory = client_and_session_factory
    login(client)
    first_response = client.post(
        "/api/workspaces/workspace-alpha/backtest-configs",
        json=config_payload("Shared name"),
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/api/workspaces/workspace-alpha/backtest-configs",
        json=config_payload("Shared name"),
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert second_response.status_code == 409
