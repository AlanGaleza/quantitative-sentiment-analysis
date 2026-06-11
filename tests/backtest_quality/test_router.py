from __future__ import annotations

from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.backtest_quality import (
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


def test_quality_route_returns_not_ready_without_s02_provider() -> None:
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 409
    assert "S-02" in response.json()["detail"]


@pytest.mark.parametrize(
    ("exc", "expected_status"),
    [
        (QualityRunNotFoundError("run not found"), 404),
        (QualityRunIncompleteError("run is incomplete"), 409),
        (QualityRunUnsupportedError("only BTCUSD BACKTEST runs are supported"), 409),
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


def test_health_endpoint_remains_unchanged() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "quantitative-sentiment-analysis"
