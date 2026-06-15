from __future__ import annotations

from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.backtest_quality import (
    LOCAL_FIXTURE_PROVIDER,
    QSA_BACKTEST_QUALITY_PROVIDER,
    QSA_RUNTIME_ENV,
    QualityInputRecord,
    QualityRunIncompleteError,
    QualityRunNotFoundError,
    QualityRunUnsupportedError,
    get_quality_input_provider,
)
from quantitative_sentiment_analysis.main import app
from tests.backtest_quality.fixtures import FixtureQualityInputProvider


class RaisingProvider:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
    ) -> Sequence[QualityInputRecord]:
        raise self.exc


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def test_quality_route_returns_fixture_backed_report() -> None:
    app.dependency_overrides[get_quality_input_provider] = (
        lambda: FixtureQualityInputProvider()
    )
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "run-001"
    assert data["instrument"] == "BTCUSD"
    assert data["mode"] == "BACKTEST"
    assert data["metrics"]["hit_rate"] == 0.75
    assert data["metrics"]["missing_movement_count"] == 1
    assert data["chart_points"][0]["outcome"] == "HIT"


def test_quality_route_returns_not_found_without_completed_dataset() -> None:
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 404
    assert "completed BACKTEST dataset" in response.json()["detail"]


def test_quality_route_returns_local_fixture_report_when_env_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(QSA_RUNTIME_ENV, "local")
    monkeypatch.setenv(QSA_BACKTEST_QUALITY_PROVIDER, LOCAL_FIXTURE_PROVIDER)
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "run-001"
    assert data["metrics"]["hit_rate"] == 0.75
    assert data["metrics"]["missing_movement_count"] == 1
    assert data["model_version"] == "sentiment-rules-v1-local-fixture"


def test_quality_route_rejects_local_fixture_provider_without_local_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(QSA_RUNTIME_ENV, raising=False)
    monkeypatch.setenv(QSA_BACKTEST_QUALITY_PROVIDER, LOCAL_FIXTURE_PROVIDER)
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 409
    assert "QSA_RUNTIME_ENV=local" in response.json()["detail"]


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (QualityRunNotFoundError("run not found"), 404),
        (QualityRunIncompleteError("run is incomplete"), 409),
    ],
)
def test_quality_route_maps_provider_errors(
    exc: Exception,
    expected_status: int,
) -> None:
    app.dependency_overrides[get_quality_input_provider] = lambda: RaisingProvider(exc)
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == expected_status
    assert response.json()["detail"] == str(exc)


@pytest.mark.parametrize(
    "detail",
    [
        "run instrument ETHUSD is unsupported; only BTCUSD quality reports are supported",
        "run mode LIVE is unsupported; only BACKTEST quality reports are supported",
    ],
)
def test_quality_route_rejects_unsupported_instrument_and_mode(
    detail: str,
) -> None:
    app.dependency_overrides[get_quality_input_provider] = (
        lambda: RaisingProvider(QualityRunUnsupportedError(detail))
    )
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 409
    assert response.json()["detail"] == detail


def test_health_endpoint_remains_unchanged() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "quantitative-sentiment-analysis"
