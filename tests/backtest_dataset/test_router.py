from __future__ import annotations

from datetime import UTC, datetime
import json

from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.backtest_dataset import (
    DatasetProviderLimitationError,
    FixtureNewsProvider,
    InMemoryCompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_dataset.provider import (
    ProviderFetchRequest,
    ProviderRawRecord,
)
from quantitative_sentiment_analysis.backtest_dataset.repository import (
    get_completed_dataset_repository,
)
from quantitative_sentiment_analysis.backtest_dataset.router import (
    get_historical_news_provider,
)
from quantitative_sentiment_analysis.backtest_shell import (
    CreateBacktestRunRequest,
    InMemoryBacktestShellRepository,
    get_backtest_shell_repository,
)
from quantitative_sentiment_analysis.main import app, create_app

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)


def draft_payload() -> dict[str, object]:
    return {
        "instrument": "BTCUSD",
        "mode": "BACKTEST",
        "timeframe_start": TIMEFRAME_START.isoformat(),
        "timeframe_end": TIMEFRAME_END.isoformat(),
    }


def fixture_records(count: int = 2) -> list[ProviderRawRecord]:
    return [
        {
            "id": f"record-{index:03d}",
            "published_at": "2026-06-02T09:00:00Z",
            "title": f"Bitcoin ETF approval sparks bullish inflows {index}",
            "source": {"id": "coinwire", "title": "CoinWire"},
        }
        for index in range(count)
    ]


def make_shell_repository() -> InMemoryBacktestShellRepository:
    return InMemoryBacktestShellRepository(
        run_id_factory=lambda workspace_id, request: "draft-run-fixed",
        clock=lambda: CREATED_AT,
    )


def create_draft(repository: InMemoryBacktestShellRepository) -> None:
    repository.create_draft_run(
        "workspace-alpha",
        CreateBacktestRunRequest.model_validate(draft_payload()),
    )


def setup_dependencies(
    *,
    shell_repository: InMemoryBacktestShellRepository | None = None,
    completed_repository: InMemoryCompletedDatasetRepository | None = None,
    provider: object | None = None,
) -> tuple[InMemoryBacktestShellRepository, InMemoryCompletedDatasetRepository]:
    app.dependency_overrides.clear()
    shell_repository = shell_repository or make_shell_repository()
    completed_repository = completed_repository or InMemoryCompletedDatasetRepository()
    provider = provider or FixtureNewsProvider(fixture_records())
    app.dependency_overrides[get_backtest_shell_repository] = lambda: shell_repository
    app.dependency_overrides[get_completed_dataset_repository] = (
        lambda: completed_repository
    )
    app.dependency_overrides[get_historical_news_provider] = lambda: provider
    return shell_repository, completed_repository


def teardown_module() -> None:
    app.dependency_overrides.clear()


def test_post_run_starts_dataset_for_existing_draft_and_get_returns_preview() -> None:
    shell_repository, _completed_repository = setup_dependencies()
    create_draft(shell_repository)
    client = TestClient(app)

    post_response = client.post(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/run"
    )

    assert post_response.status_code == 200
    post_data = post_response.json()
    assert post_data["summary"]["workspace_id"] == "workspace-alpha"
    assert post_data["summary"]["run_id"] == "draft-run-fixed"
    assert post_data["summary"]["status"] == "COMPLETED"
    assert post_data["summary"]["provider_name"] == "FixtureNews"
    assert post_data["summary"]["record_count"] == 2
    assert post_data["records"][0]["directional_bias"] == "LONG"

    get_response = client.get(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset"
    )

    assert get_response.status_code == 200
    assert get_response.json() == post_data


def test_post_run_returns_404_for_missing_draft_run() -> None:
    setup_dependencies()
    client = TestClient(app)

    response = client.post(
        "/api/workspaces/workspace-alpha/backtests/missing-run/dataset/run"
    )

    assert response.status_code == 404
    assert "missing-run" in response.json()["detail"]


def test_post_run_uses_workspace_boundary() -> None:
    shell_repository, _completed_repository = setup_dependencies()
    create_draft(shell_repository)
    client = TestClient(app)

    response = client.post(
        "/api/workspaces/workspace-beta/backtests/draft-run-fixed/dataset/run"
    )

    assert response.status_code == 404


def test_post_run_maps_provider_limitation_to_409_with_typed_failed_state() -> None:
    class ProviderLimited:
        provider_name = "CryptoPanic"

        def fetch_historical_news(
            self,
            request: ProviderFetchRequest,
        ) -> tuple[ProviderRawRecord, ...]:
            raise DatasetProviderLimitationError(
                provider_name=self.provider_name,
                reason="missing provider configuration",
                detail="Set CRYPTOPANIC_API_KEY locally for a BACKTEST smoke check.",
            )

    shell_repository, _completed_repository = setup_dependencies(provider=ProviderLimited())
    create_draft(shell_repository)
    client = TestClient(app)

    response = client.post(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/run"
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["summary"]["status"] == "FAILED_PROVIDER_LIMITATION"
    assert detail["summary"]["provider_limitation"]["provider_name"] == "CryptoPanic"
    assert detail["summary"]["provider_limitation"]["reason"] == (
        "missing provider configuration"
    )
    assert "BACKTEST" in detail["summary"]["provider_limitation"]["detail"]


def test_get_dataset_returns_404_for_missing_completed_dataset() -> None:
    setup_dependencies()
    client = TestClient(app)

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset"
    )

    assert response.status_code == 404
    assert "completed BACKTEST dataset" in response.json()["detail"]


def test_dataset_preview_is_bounded() -> None:
    shell_repository, _completed_repository = setup_dependencies(
        provider=FixtureNewsProvider(fixture_records(count=105))
    )
    create_draft(shell_repository)
    client = TestClient(app)

    response = client.post(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/run"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["record_count"] == 105
    assert len(data["records"]) == 100


def test_export_dataset_jsonl_returns_full_completed_dataset_with_download_headers() -> None:
    shell_repository, _completed_repository = setup_dependencies(
        provider=FixtureNewsProvider(fixture_records(count=105))
    )
    create_draft(shell_repository)
    client = TestClient(app)

    post_response = client.post(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/run"
    )
    assert post_response.status_code == 200
    assert len(post_response.json()["records"]) == 100

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/export.jsonl"
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert response.headers["content-disposition"] == (
        'attachment; filename="workspace-alpha-draft-run-fixed-dataset.jsonl"'
    )
    assert response.headers["x-qsa-workspace-id"] == "workspace-alpha"
    assert response.headers["x-qsa-run-id"] == "draft-run-fixed"
    assert response.headers["x-qsa-config-version"] == "news-sentiment-policy-v1"
    assert response.content.endswith(b"\n")

    lines = response.content.decode("utf-8").splitlines()
    assert len(lines) == 105
    payloads = [json.loads(line) for line in lines]
    assert payloads[0]["record_id"] == "fixturenews:record-000"
    assert payloads[-1]["record_id"] == "fixturenews:record-104"
    assert all(payload["run_id"] == "draft-run-fixed" for payload in payloads)
    assert all(payload["config_version"] == "news-sentiment-policy-v1" for payload in payloads)
    assert "provider_name" not in payloads[0]


def test_export_dataset_jsonl_returns_404_for_missing_completed_dataset_without_provider_call() -> None:
    class ProviderShouldNotBeCalled:
        provider_name = "UnexpectedProvider"

        def fetch_historical_news(
            self,
            request: ProviderFetchRequest,
        ) -> tuple[ProviderRawRecord, ...]:
            raise AssertionError("export must not trigger dataset generation")

    setup_dependencies(provider=ProviderShouldNotBeCalled())
    client = TestClient(app)

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/missing-run/dataset/export.jsonl"
    )

    assert response.status_code == 404
    assert "completed BACKTEST dataset" in response.json()["detail"]


def test_export_dataset_jsonl_uses_workspace_boundary() -> None:
    shell_repository, _completed_repository = setup_dependencies()
    create_draft(shell_repository)
    client = TestClient(app)
    post_response = client.post(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/run"
    )
    assert post_response.status_code == 200

    response = client.get(
        "/api/workspaces/workspace-beta/backtests/draft-run-fixed/dataset/export.jsonl"
    )

    assert response.status_code == 404


def test_export_dataset_jsonl_returns_409_for_provider_limited_dataset() -> None:
    class ProviderLimited:
        provider_name = "CryptoPanic"

        def fetch_historical_news(
            self,
            request: ProviderFetchRequest,
        ) -> tuple[ProviderRawRecord, ...]:
            raise DatasetProviderLimitationError(
                provider_name=self.provider_name,
                reason="missing provider configuration",
                detail="Set CRYPTOPANIC_API_KEY locally for a BACKTEST smoke check.",
            )

    shell_repository, _completed_repository = setup_dependencies(provider=ProviderLimited())
    create_draft(shell_repository)
    client = TestClient(app)
    post_response = client.post(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/run"
    )
    assert post_response.status_code == 409

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/export.jsonl"
    )

    assert response.status_code == 409
    assert "COMPLETED deterministic dataset" in response.json()["detail"]


def test_cors_preflight_allows_dataset_post_route() -> None:
    client = TestClient(
        create_app(cors_allowed_origins=["https://frontend.example.test"])
    )

    response = client.options(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/run",
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


def test_cors_preflight_allows_dataset_export_route() -> None:
    client = TestClient(
        create_app(cors_allowed_origins=["https://frontend.example.test"])
    )

    response = client.options(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/dataset/export.jsonl",
        headers={
            "Origin": "https://frontend.example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://frontend.example.test"
    )
