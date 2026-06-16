from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.auth.dependencies import require_owned_workspace
from quantitative_sentiment_analysis.backtest_dataset.repository import (
    PostgresCompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetRunStatus,
    DatasetRunSummary,
)
from quantitative_sentiment_analysis.backtest_shell.repository import (
    PostgresBacktestShellRepository,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import (
    CreateBacktestRunRequest,
)
from quantitative_sentiment_analysis.backtest_quality import (
    LOCAL_FIXTURE_PROVIDER,
    QSA_BACKTEST_QUALITY_PROVIDER,
    QSA_RUNTIME_ENV,
    QualityHorizon,
    QualityInputBatch,
    QualityRunIncompleteError,
    QualityRunNotFoundError,
    QualityRunUnsupportedError,
    get_quality_input_provider,
)
from quantitative_sentiment_analysis.backtest_quality.schemas import RealizedDirection
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.main import app
from quantitative_sentiment_analysis.main import create_app
from quantitative_sentiment_analysis.persistence.database import (
    create_session_factory,
    reset_database_state_for_tests,
)
from quantitative_sentiment_analysis.price_enrichment.binance import (
    BINANCE_SPOT_PROVIDER_NAME,
)
from quantitative_sentiment_analysis.price_enrichment.repository import (
    PostgresPriceCandleRepository,
)
from quantitative_sentiment_analysis.price_enrichment.schemas import PriceCandle
from tests.backtest_quality.fixtures import (
    FixtureQualityInputProvider,
    make_quality_record,
)
from tests.postgres_helpers import (
    FRONTEND_ORIGIN,
    clear_database,
    login,
    override_database_session,
    postgres_engine_or_skip,
    seed_user_with_workspace,
)


class RaisingProvider:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
        horizon: QualityHorizon,
    ) -> QualityInputBatch:
        raise self.exc


class PartialWarningProvider:
    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
        horizon: QualityHorizon,
    ) -> QualityInputBatch:
        return QualityInputBatch(
            records=[
                make_quality_record(
                    1,
                    workspace_id=workspace_id,
                    run_id=run_id,
                    sentiment_score=0.7,
                    directional_bias=DirectionalBias.LONG,
                    later_return=None,
                    realized_direction=None,
                )
            ],
            extra_warnings=(
                "Price provider was unavailable; price movement remains partial.",
            ),
        )


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_owned_workspace] = lambda: object()
    yield
    app.dependency_overrides.clear()


def test_quality_route_returns_fixture_backed_report() -> None:
    app.dependency_overrides[get_quality_input_provider] = lambda: (
        FixtureQualityInputProvider()
    )
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "run-001"
    assert data["instrument"] == "BTCUSD"
    assert data["mode"] == "BACKTEST"
    assert data["horizon"] == {"value": 4, "unit": "hours"}
    assert data["metrics"]["hit_rate"] == 0.75
    assert data["metrics"]["missing_movement_count"] == 1
    assert data["chart_points"][0]["outcome"] == "HIT"


def test_quality_route_returns_deterministic_json_response() -> None:
    app.dependency_overrides[get_quality_input_provider] = lambda: (
        FixtureQualityInputProvider()
    )
    client = TestClient(app)
    url = (
        "/api/workspaces/workspace-alpha/backtests/run-001/quality"
        "?horizon_value=1&horizon_unit=minutes"
    )

    first_response = client.get(url)
    second_response = client.get(url)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()


def test_quality_route_accepts_supported_selected_horizon() -> None:
    fixture_provider = FixtureQualityInputProvider()
    app.dependency_overrides[get_quality_input_provider] = lambda: fixture_provider
    client = TestClient(app)

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/run-001/quality"
        "?horizon_value=1&horizon_unit=minutes"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["horizon"] == {"value": 1, "unit": "minutes"}
    assert data["metrics"]["hit_rate"] == 0.75
    assert data["metrics"]["missing_movement_count"] == 1


def test_quality_route_rejects_unsupported_horizon() -> None:
    app.dependency_overrides[get_quality_input_provider] = lambda: (
        FixtureQualityInputProvider()
    )
    client = TestClient(app)

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/run-001/quality"
        "?horizon_value=2&horizon_unit=hours"
    )

    assert response.status_code == 422
    assert "unsupported quality horizon" in response.json()["detail"]
    assert "1 minute" in response.json()["detail"]
    assert "4 hours" in response.json()["detail"]


def test_quality_route_returns_not_found_without_completed_dataset() -> None:
    app.dependency_overrides[get_quality_input_provider] = lambda: RaisingProvider(
        QualityRunNotFoundError("completed BACKTEST dataset not found")
    )
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


def test_quality_route_returns_partial_report_with_enrichment_warning() -> None:
    app.dependency_overrides[get_quality_input_provider] = lambda: PartialWarningProvider()
    client = TestClient(app)

    response = client.get("/api/workspaces/workspace-alpha/backtests/run-001/quality")

    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["missing_movement_count"] == 1
    assert data["representative_records"][0]["later_return"] is None
    assert any("Price provider was unavailable" in warning for warning in data["warnings"])


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
    app.dependency_overrides[get_quality_input_provider] = lambda: RaisingProvider(
        QualityRunUnsupportedError(detail)
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


def test_postgres_quality_route_reads_persisted_completed_dataset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = postgres_engine_or_skip(monkeypatch)
    session_factory = create_session_factory(engine)
    test_app = create_app(cors_allowed_origins=[FRONTEND_ORIGIN])
    override_database_session(test_app, engine)
    with session_factory() as session:
        clear_database(session)
        seed_user_with_workspace(session, workspace_slug="workspace-alpha")
        PostgresBacktestShellRepository(
            session,
            run_id_factory=lambda workspace_id, request: "draft-run-fixed",
        ).create_draft_run(
            "workspace-alpha",
            CreateBacktestRunRequest(
                timeframe_start=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
                timeframe_end=datetime(2026, 6, 8, 12, 0, tzinfo=UTC),
            ),
        )
        PostgresCompletedDatasetRepository(session).save_run(
            DatasetRunSummary(
                workspace_id="workspace-alpha",
                run_id="draft-run-fixed",
                timeframe_start=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
                timeframe_end=datetime(2026, 6, 8, 12, 0, tzinfo=UTC),
                status=DatasetRunStatus.COMPLETED,
                provider_name="FixtureNews",
                record_count=1,
                relevant_count=1,
                noise_count=0,
                irrelevant_count=0,
                model_version="sentiment-rules-v1",
                config_version="news-sentiment-policy-v1",
                input_fingerprint="fingerprint-alpha",
            ),
            [
                DatasetRecord(
                    workspace_id="workspace-alpha",
                    run_id="draft-run-fixed",
                    record_id="record-001",
                    timestamp=datetime(2026, 6, 2, 9, 30, tzinfo=UTC),
                    headline="Bitcoin ETF approval sparks bullish inflows",
                    source_name="FixtureNews",
                    sentiment_score=0.75,
                    directional_bias=DirectionalBias.LONG,
                    confidence=0.8,
                    relevance=RelevanceLabel.RELEVANT,
                    model_version="sentiment-rules-v1",
                    config_version="news-sentiment-policy-v1",
                )
            ],
        )
        PostgresPriceCandleRepository(session).upsert_candles(
            [
                PriceCandle(
                    provider_name=BINANCE_SPOT_PROVIDER_NAME,
                    symbol="BTCUSDT",
                    interval="1m",
                    open_time=datetime(2026, 6, 2, 9, 30, tzinfo=UTC),
                    close_time=datetime(2026, 6, 2, 9, 31, tzinfo=UTC),
                    open_price=100.0,
                    high_price=100.0,
                    low_price=100.0,
                    close_price=100.0,
                ),
                PriceCandle(
                    provider_name=BINANCE_SPOT_PROVIDER_NAME,
                    symbol="BTCUSDT",
                    interval="1m",
                    open_time=datetime(2026, 6, 2, 9, 31, tzinfo=UTC),
                    close_time=datetime(2026, 6, 2, 9, 32, tzinfo=UTC),
                    open_price=101.0,
                    high_price=101.0,
                    low_price=101.0,
                    close_price=101.0,
                ),
            ]
        )

    with TestClient(test_app, base_url="https://api.example.test") as client:
        login(client)
        response = client.get(
            "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/quality"
            "?horizon_value=1&horizon_unit=minutes"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "draft-run-fixed"
    assert data["horizon"] == {"value": 1, "unit": "minutes"}
    assert data["metrics"]["missing_movement_count"] == 0
    assert data["representative_records"][0]["later_return"] == pytest.approx(0.01)
    assert data["representative_records"][0]["realized_direction"] == (
        RealizedDirection.UP
    )
    assert not any("missing later movement" in warning for warning in data["warnings"])
    assert "S-02" not in str(data)
    with session_factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()
