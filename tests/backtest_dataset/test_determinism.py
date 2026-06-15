from __future__ import annotations

from datetime import UTC, datetime

from quantitative_sentiment_analysis.backtest_dataset import (
    DatasetOrchestrator,
    FixtureNewsProvider,
    InMemoryCompletedDatasetRepository,
    metadata_for_preview,
)
from quantitative_sentiment_analysis.backtest_shell import (
    CreateBacktestRunRequest,
    InMemoryBacktestShellRepository,
)
from quantitative_sentiment_analysis.contracts import stable_json_dumps
from quantitative_sentiment_analysis.sentiment_policy import SentimentPolicyConfig

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
CREATED_AT = datetime(2026, 6, 8, 12, 30, tzinfo=UTC)


def run_preview(
    *,
    records: list[dict[str, object]] | None = None,
    policy_config: SentimentPolicyConfig | None = None,
    seed: int = 42,
    timeframe_end: datetime = TIMEFRAME_END,
) -> str:
    shell_repository = InMemoryBacktestShellRepository(
        run_id_factory=lambda workspace_id, request: "draft-run-000001",
        clock=lambda: CREATED_AT,
    )
    shell_repository.create_draft_run(
        "workspace-alpha",
        CreateBacktestRunRequest(
            timeframe_start=TIMEFRAME_START,
            timeframe_end=timeframe_end,
        ),
    )
    orchestrator = DatasetOrchestrator(
        shell_repository=shell_repository,
        completed_repository=InMemoryCompletedDatasetRepository(),
        provider=FixtureNewsProvider(records or fixture_records()),
        policy_config=policy_config or SentimentPolicyConfig(),
        seed=seed,
    )
    preview = orchestrator.run_dataset(
        workspace_id="workspace-alpha",
        run_id="draft-run-000001",
    )
    return stable_json_dumps(
        {
            "preview": preview,
            "metadata": metadata_for_preview(preview=preview, seed=seed),
        }
    )


def fixture_records() -> list[dict[str, object]]:
    return [
        {
            "id": "positive-btc",
            "published_at": "2026-06-02T09:00:00Z",
            "title": "Bitcoin ETF approval sparks bullish institutional inflows",
            "source": {"id": "coinwire", "title": "CoinWire"},
        },
        {
            "id": "negative-btc",
            "published_at": "2026-06-02T10:00:00Z",
            "title": "BTC selloff follows regulatory crackdown",
            "source_name": "Crypto Desk",
        },
    ]


def test_serialized_preview_is_stable_for_identical_inputs() -> None:
    assert run_preview() == run_preview()


def test_serialized_preview_is_stable_for_reordered_equivalent_provider_input() -> None:
    assert run_preview(records=fixture_records()) == run_preview(
        records=list(reversed(fixture_records()))
    )


def test_fingerprint_changes_when_normalized_input_changes() -> None:
    baseline = run_preview()
    changed_records = fixture_records()
    changed_records[0] = {
        **changed_records[0],
        "title": "Bitcoin ETF rejection sparks bearish outflows",
    }

    assert run_preview(records=changed_records) != baseline


def test_fingerprint_changes_when_config_seed_or_timeframe_changes() -> None:
    baseline = run_preview()

    assert run_preview(seed=43) != baseline
    assert (
        run_preview(
            policy_config=SentimentPolicyConfig(
                model_version="sentiment-rules-v2",
            )
        )
        != baseline
    )
    assert (
        run_preview(
            policy_config=SentimentPolicyConfig(
                config_version="news-sentiment-policy-v2",
            )
        )
        != baseline
    )
    assert run_preview(timeframe_end=datetime(2026, 6, 9, 12, 0, tzinfo=UTC)) != baseline
