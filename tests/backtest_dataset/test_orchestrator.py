from __future__ import annotations

from datetime import UTC, datetime

from quantitative_sentiment_analysis.backtest_dataset import (
    DatasetOrchestrator,
    DatasetProviderLimitationError,
    DatasetRunStatus,
    FixtureNewsProvider,
    InMemoryCompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_dataset.provider import (
    ProviderFetchRequest,
    ProviderRawRecord,
)
from quantitative_sentiment_analysis.backtest_shell import (
    CreateBacktestRunRequest,
    InMemoryBacktestShellRepository,
)
from quantitative_sentiment_analysis.contracts import DirectionalBias, RelevanceLabel

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)


def make_shell_repository() -> InMemoryBacktestShellRepository:
    repository = InMemoryBacktestShellRepository(
        run_id_factory=lambda workspace_id, request: "draft-run-000001",
        clock=lambda: CREATED_AT,
    )
    repository.create_draft_run(
        "workspace-alpha",
        CreateBacktestRunRequest(
            timeframe_start=TIMEFRAME_START,
            timeframe_end=TIMEFRAME_END,
        ),
    )
    return repository


def raw_records() -> list[ProviderRawRecord]:
    return [
        {
            "id": "positive-btc",
            "published_at": "2026-06-02T09:00:00Z",
            "title": "Bitcoin ETF approval sparks bullish institutional inflows",
            "source": {"id": "coinwire", "title": "CoinWire"},
        },
        {
            "id": "missing-source",
            "published_at": "2026-06-02T10:00:00Z",
            "title": "Bitcoin placeholder update",
        },
        {
            "id": "irrelevant-eth",
            "published_at": "2026-06-02T11:00:00Z",
            "title": "Ethereum upgrade supports ETH ecosystem",
            "source_name": "Crypto Desk",
        },
    ]


def run_orchestrator(
    records: list[ProviderRawRecord],
    *,
    repository: InMemoryCompletedDatasetRepository | None = None,
) -> tuple[DatasetOrchestrator, InMemoryCompletedDatasetRepository]:
    completed_repository = repository or InMemoryCompletedDatasetRepository()
    orchestrator = DatasetOrchestrator(
        shell_repository=make_shell_repository(),
        completed_repository=completed_repository,
        provider=FixtureNewsProvider(records),
    )
    return orchestrator, completed_repository


def test_orchestrator_generates_completed_dataset_from_draft_shell() -> None:
    orchestrator, repository = run_orchestrator(raw_records())

    preview = orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )

    assert preview.summary.status is DatasetRunStatus.COMPLETED
    assert preview.summary.workspace_id == "workspace-alpha"
    assert preview.summary.run_id == "draft-run-000001"
    assert preview.summary.timeframe_start == TIMEFRAME_START
    assert preview.summary.timeframe_end == TIMEFRAME_END
    assert preview.summary.provider_name == "FixtureNews"
    assert preview.summary.record_count == 3
    assert preview.summary.relevant_count == 1
    assert preview.summary.noise_count == 1
    assert preview.summary.irrelevant_count == 1
    assert preview.summary.model_version == "sentiment-rules-v1"
    assert preview.summary.config_version == "news-sentiment-policy-v1"
    assert preview.summary.input_fingerprint

    records = repository.list_records("workspace-alpha", "draft-run-000001")
    assert len(records) == 3
    assert records[0].record_id == "fixturenews:positive-btc"
    assert records[0].directional_bias is DirectionalBias.LONG
    assert records[0].relevance is RelevanceLabel.RELEVANT
    assert records[1].relevance is RelevanceLabel.NOISE
    assert records[1].source_name == "FixtureNews"
    assert records[1].sentiment_score == 0.0
    assert records[1].directional_bias is DirectionalBias.FLAT
    assert records[2].relevance is RelevanceLabel.IRRELEVANT
    assert records[2].sentiment_score == 0.0


def test_orchestrator_repeated_runs_are_identical() -> None:
    first_orchestrator, _first_repository = run_orchestrator(raw_records())
    second_orchestrator, _second_repository = run_orchestrator(raw_records())

    first = first_orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )
    second = second_orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )

    assert first == second


def test_orchestrator_is_stable_for_reordered_provider_records() -> None:
    first_orchestrator, first_repository = run_orchestrator(raw_records())
    second_orchestrator, second_repository = run_orchestrator(list(reversed(raw_records())))

    first = first_orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )
    second = second_orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )

    assert first.summary.input_fingerprint == second.summary.input_fingerprint
    assert first_repository.list_records(
        "workspace-alpha",
        "draft-run-000001",
    ) == second_repository.list_records("workspace-alpha", "draft-run-000001")


def test_orchestrator_stores_provider_limitation_state() -> None:
    class ProviderLimited:
        provider_name = "Sharpe Terminal"

        def fetch_historical_news(
            self,
            request: ProviderFetchRequest,
        ) -> tuple[ProviderRawRecord, ...]:
            raise DatasetProviderLimitationError(
                provider_name=self.provider_name,
                reason="missing provider configuration",
                detail="Set SHARPE_API_KEY for a manual BACKTEST smoke check.",
            )

    repository = InMemoryCompletedDatasetRepository()
    orchestrator = DatasetOrchestrator(
        shell_repository=make_shell_repository(),
        completed_repository=repository,
        provider=ProviderLimited(),
    )

    preview = orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )

    assert preview.summary.status is DatasetRunStatus.FAILED_PROVIDER_LIMITATION
    assert preview.summary.provider_name == "Sharpe Terminal"
    assert preview.summary.record_count == 0
    assert preview.summary.provider_limitation is not None
    assert preview.summary.provider_limitation.reason == "missing provider configuration"
    assert repository.list_records("workspace-alpha", "draft-run-000001") == ()


def test_orchestrator_preview_is_bounded_but_repository_keeps_records() -> None:
    records = [
        {
            "id": f"record-{index:03d}",
            "published_at": "2026-06-02T09:00:00Z",
            "title": f"Bitcoin ETF approval headline {index}",
            "source_name": "Crypto Desk",
        }
        for index in range(105)
    ]
    orchestrator, repository = run_orchestrator(records)

    preview = orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )

    assert preview.summary.record_count == 105
    assert len(preview.records) == 100
    assert len(repository.list_records("workspace-alpha", "draft-run-000001")) == 105
