from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.auth.dependencies import require_owned_workspace
from quantitative_sentiment_analysis.backtest_shell import (
    BacktestRunShell,
    CreateBacktestRunRequest,
    InMemoryBacktestShellRepository,
    get_backtest_shell_repository,
)
from quantitative_sentiment_analysis.main import app, create_app
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
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)


def draft_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "instrument": "BTCUSD",
        "mode": "BACKTEST",
        "timeframe_start": TIMEFRAME_START.isoformat(),
        "timeframe_end": TIMEFRAME_END.isoformat(),
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_owned_workspace] = lambda: object()
    yield
    app.dependency_overrides.clear()


def make_repository() -> InMemoryBacktestShellRepository:
    return InMemoryBacktestShellRepository(
        run_id_factory=lambda workspace_id, request: "draft-run-fixed",
        clock=lambda: CREATED_AT,
    )


def test_create_draft_run_returns_workspace_scoped_backtest_shell() -> None:
    repository = make_repository()
    app.dependency_overrides[get_backtest_shell_repository] = lambda: repository
    client = TestClient(app)

    response = client.post(
        "/api/workspaces/workspace-alpha/backtests/drafts",
        json=draft_payload(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "draft-run-fixed"
    assert data["instrument"] == "BTCUSD"
    assert data["mode"] == "BACKTEST"
    assert data["status"] == "DRAFT"
    assert data["quality_report_path"] == (
        "/workspaces/workspace-alpha/backtests/draft-run-fixed/quality"
    )


def test_get_draft_run_uses_workspace_and_run_id() -> None:
    repository = make_repository()
    request = CreateBacktestRunRequest.model_validate(draft_payload())
    run = repository.create_draft_run("workspace-alpha", request)
    app.dependency_overrides[get_backtest_shell_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(
        f"/api/workspaces/workspace-alpha/backtests/{run.run_id}",
    )

    assert response.status_code == 200
    assert response.json()["workspace_id"] == "workspace-alpha"
    assert response.json()["run_id"] == run.run_id


def test_get_draft_run_returns_404_for_missing_run() -> None:
    repository = make_repository()
    app.dependency_overrides[get_backtest_shell_repository] = lambda: repository
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/missing-run")

    assert response.status_code == 404
    assert "local/dev" in response.json()["detail"]


def test_get_draft_run_returns_404_for_cross_workspace_read() -> None:
    repository = make_repository()
    request = CreateBacktestRunRequest.model_validate(draft_payload())
    run = repository.create_draft_run("workspace-alpha", request)
    app.dependency_overrides[get_backtest_shell_repository] = lambda: repository
    client = TestClient(app)

    response = client.get(f"/api/workspaces/workspace-beta/backtests/{run.run_id}")

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        draft_payload(timeframe_end=datetime(2026, 7, 2, 12, 0, tzinfo=UTC).isoformat()),
        draft_payload(
            timeframe_start=TIMEFRAME_END.isoformat(),
            timeframe_end=TIMEFRAME_START.isoformat(),
        ),
        draft_payload(timeframe_start="2026-06-01T12:00:00"),
    ],
)
def test_create_draft_run_rejects_invalid_timeframes(
    payload: dict[str, object],
) -> None:
    app.dependency_overrides[get_backtest_shell_repository] = lambda: make_repository()
    client = TestClient(app)

    response = client.post(
        "/api/workspaces/workspace-alpha/backtests/drafts",
        json=payload,
    )

    assert response.status_code == 422


def test_create_draft_run_does_not_start_dataset_or_quality_work() -> None:
    class CreateOnlyRepository:
        def create_draft_run(
            self,
            workspace_id: str,
            request: CreateBacktestRunRequest,
        ) -> BacktestRunShell:
            return BacktestRunShell(
                workspace_id=workspace_id,
                run_id="draft-run-fixed",
                timeframe_start=request.timeframe_start,
                timeframe_end=request.timeframe_end,
                created_at=CREATED_AT,
                quality_report_path=(
                    "/workspaces/workspace-alpha/backtests/draft-run-fixed/quality"
                ),
            )

        def get_run(self, workspace_id: str, run_id: str) -> BacktestRunShell:
            raise AssertionError("create route must not fetch completed quality inputs")

    app.dependency_overrides[get_backtest_shell_repository] = lambda: CreateOnlyRepository()
    client = TestClient(app)

    response = client.post(
        "/api/workspaces/workspace-alpha/backtests/drafts",
        json=draft_payload(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "DRAFT"


def test_cors_preflight_allows_configured_frontend_post_origin() -> None:
    client = TestClient(
        create_app(cors_allowed_origins=["https://frontend.example.test"])
    )

    response = client.options(
        "/api/workspaces/workspace-alpha/backtests/drafts",
        headers={
            "Origin": "https://frontend.example.test",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://frontend.example.test"
    )


def test_cors_preflight_rejects_unconfigured_frontend_post_origin() -> None:
    client = TestClient(
        create_app(cors_allowed_origins=["https://frontend.example.test"])
    )

    response = client.options(
        "/api/workspaces/workspace-alpha/backtests/drafts",
        headers={
            "Origin": "https://other.example.test",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_postgres_shell_route_requires_authenticated_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = postgres_engine_or_skip(monkeypatch)
    session_factory = create_session_factory(engine)
    test_app = create_app(cors_allowed_origins=[FRONTEND_ORIGIN])
    override_database_session(test_app, engine)
    with session_factory() as session:
        clear_database(session)
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")

    with TestClient(test_app, base_url="https://api.example.test") as client:
        response = client.post(
            "/api/workspaces/workspace-alpha/backtests/drafts",
            json=draft_payload(),
            headers={"Origin": FRONTEND_ORIGIN},
        )

    assert response.status_code == 401
    with session_factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()


def test_postgres_shell_route_authenticated_owner_creates_and_reads_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = postgres_engine_or_skip(monkeypatch)
    session_factory = create_session_factory(engine)
    test_app = create_app(cors_allowed_origins=[FRONTEND_ORIGIN])
    override_database_session(test_app, engine)
    with session_factory() as session:
        clear_database(session)
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")

    with TestClient(test_app, base_url="https://api.example.test") as client:
        login(client)
        create_response = client.post(
            "/api/workspaces/workspace-alpha/backtests/drafts",
            json=draft_payload(),
            headers={"Origin": FRONTEND_ORIGIN},
        )
        assert create_response.status_code == 200
        run_id = create_response.json()["run_id"]

        get_response = client.get(f"/api/workspaces/workspace-alpha/backtests/{run_id}")

    assert get_response.status_code == 200
    assert get_response.json()["workspace_id"] == "workspace-alpha"
    assert get_response.json()["run_id"] == run_id
    with session_factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()


def test_postgres_shell_route_returns_404_for_cross_owned_workspace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        login(client)
        response = client.post(
            "/api/workspaces/workspace-beta/backtests/drafts",
            json=draft_payload(),
            headers={"Origin": FRONTEND_ORIGIN},
        )

    assert response.status_code == 404
    with session_factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()
