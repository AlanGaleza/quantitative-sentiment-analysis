from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.auth.dependencies import require_owned_workspace
from quantitative_sentiment_analysis.backtest_dataset import (
    DatasetProviderLimitation,
    DatasetRunStatus,
    DatasetRunSummary,
    InMemoryCompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_quality import (
    CompletedDatasetQualityInputProvider,
    QualityRunIncompleteError,
    QualityRunNotFoundError,
    get_quality_input_provider,
)
from quantitative_sentiment_analysis.backtest_quality.schemas import (
    HorizonUnit,
    QualityHorizon,
    RealizedDirection,
)
from quantitative_sentiment_analysis.contracts import (
    DatasetRecord,
    DirectionalBias,
    RelevanceLabel,
)
from quantitative_sentiment_analysis.main import app
from quantitative_sentiment_analysis.price_enrichment.provider import (
    FixturePriceProvider,
    PriceFetchRequest,
    PriceProviderUnavailableError,
)
from quantitative_sentiment_analysis.price_enrichment.repository import (
    PriceCandleRepository,
)
from quantitative_sentiment_analysis.price_enrichment.schemas import PriceCandle
from quantitative_sentiment_analysis.price_enrichment.service import (
    PriceEnrichmentService,
)

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
EVENT_TIME = datetime(2026, 6, 2, 9, 30, tzinfo=UTC)
ONE_MINUTE = QualityHorizon(value=1, unit=HorizonUnit.MINUTES)
FOUR_HOURS = QualityHorizon(value=4, unit=HorizonUnit.HOURS)


class InMemoryPriceCandleRepository:
    def __init__(self, candles: Iterable[PriceCandle] = ()) -> None:
        self._candles: dict[tuple[str, str, str, datetime], PriceCandle] = {}
        self.upsert_candles(candles)

    def upsert_candles(self, candles: Iterable[PriceCandle]) -> tuple[PriceCandle, ...]:
        stored = tuple(PriceCandle.model_validate(candle.model_dump()) for candle in candles)
        for candle in stored:
            self._candles[
                (
                    candle.provider_name,
                    candle.symbol,
                    candle.interval,
                    candle.open_time,
                )
            ] = candle
        return tuple(sorted(stored, key=lambda candle: candle.open_time))

    def list_candles(
        self,
        *,
        provider_name: str,
        symbol: str,
        interval: str,
        start_open_time: datetime,
        end_open_time: datetime,
    ) -> tuple[PriceCandle, ...]:
        return tuple(
            candle
            for candle in sorted(self._candles.values(), key=lambda item: item.open_time)
            if candle.provider_name == provider_name
            and candle.symbol == symbol
            and candle.interval == interval
            and start_open_time <= candle.open_time <= end_open_time
        )

    def get_candles_by_open_time(
        self,
        *,
        provider_name: str,
        symbol: str,
        interval: str,
        open_times: Iterable[datetime],
    ) -> dict[datetime, PriceCandle]:
        requested_open_times = tuple(open_times)
        return {
            open_time: candle
            for open_time in requested_open_times
            if (
                candle := self._candles.get(
                    (provider_name, symbol, interval, open_time)
                )
            )
            is not None
        }


class FailingPriceProvider:
    provider_name = "FixturePrice"

    def fetch_price_candles(
        self,
        request: PriceFetchRequest,
    ) -> tuple[PriceCandle, ...]:
        raise PriceProviderUnavailableError("fixture price provider unavailable")


def make_summary(**overrides: object) -> DatasetRunSummary:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-fixed",
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
        "status": DatasetRunStatus.COMPLETED,
        "provider_name": "FixtureNews",
        "record_count": 2,
        "relevant_count": 1,
        "noise_count": 1,
        "irrelevant_count": 0,
        "model_version": "sentiment-rules-v1",
        "config_version": "news-sentiment-policy-v1",
        "input_fingerprint": "fingerprint-alpha",
    }
    payload.update(overrides)
    return DatasetRunSummary.model_validate(payload)


def make_record(index: int, **overrides: object) -> DatasetRecord:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-fixed",
        "record_id": f"record-{index:03d}",
        "timestamp": EVENT_TIME,
        "headline": f"Bitcoin ETF approval headline {index}",
        "source_name": "FixtureNews",
        "sentiment_score": 0.45,
        "directional_bias": DirectionalBias.LONG,
        "confidence": 0.72,
        "relevance": RelevanceLabel.RELEVANT,
        "model_version": "sentiment-rules-v1",
        "config_version": "news-sentiment-policy-v1",
    }
    payload.update(overrides)
    return DatasetRecord.model_validate(payload)


def make_candle(open_time: datetime, *, close_price: float) -> PriceCandle:
    return PriceCandle(
        provider_name="FixturePrice",
        symbol="BTCUSDT",
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open_price=close_price,
        high_price=close_price,
        low_price=close_price,
        close_price=close_price,
    )


def make_repository(
    records: list[DatasetRecord] | None = None,
    **summary_overrides: object,
) -> InMemoryCompletedDatasetRepository:
    stored_records = records or [
        make_record(1),
        make_record(
            2,
            headline="Provider placeholder",
            sentiment_score=0.0,
            directional_bias=DirectionalBias.FLAT,
            relevance=RelevanceLabel.NOISE,
        ),
    ]
    summary_defaults = {
        "record_count": len(stored_records),
        "relevant_count": sum(
            record.relevance is RelevanceLabel.RELEVANT for record in stored_records
        ),
        "noise_count": sum(
            record.relevance is RelevanceLabel.NOISE for record in stored_records
        ),
        "irrelevant_count": sum(
            record.relevance is RelevanceLabel.IRRELEVANT for record in stored_records
        ),
    }
    summary_defaults.update(summary_overrides)
    repository = InMemoryCompletedDatasetRepository()
    repository.save_run(make_summary(**summary_defaults), stored_records)
    return repository


def make_service(
    candles: Iterable[PriceCandle] = (),
    *,
    repository: PriceCandleRepository | None = None,
) -> PriceEnrichmentService:
    candle_repository = repository or InMemoryPriceCandleRepository()
    return PriceEnrichmentService(
        candle_repository=candle_repository,
        price_provider=FixturePriceProvider(tuple(candles)),
    )


def make_provider(
    *,
    repository: InMemoryCompletedDatasetRepository | None = None,
    service: PriceEnrichmentService | None = None,
) -> CompletedDatasetQualityInputProvider:
    return CompletedDatasetQualityInputProvider(
        repository or make_repository(),
        service
        or make_service(
            [
                make_candle(EVENT_TIME, close_price=100.0),
                make_candle(EVENT_TIME + timedelta(minutes=1), close_price=101.0),
            ]
        ),
    )


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    app.dependency_overrides[require_owned_workspace] = lambda: object()
    yield
    app.dependency_overrides.clear()


def test_adapter_enriches_completed_dataset_with_one_minute_price_movement() -> None:
    provider = make_provider()

    batch = provider.get_quality_inputs(
        "workspace-alpha",
        "draft-run-fixed",
        ONE_MINUTE,
    )

    assert len(batch.records) == 2
    assert batch.extra_warnings == ()
    assert batch.records[0].workspace_id == "workspace-alpha"
    assert batch.records[0].run_id == "draft-run-fixed"
    assert batch.records[0].event_timestamp == EVENT_TIME
    assert batch.records[0].later_return == pytest.approx(0.01)
    assert batch.records[0].realized_direction is RealizedDirection.UP
    assert batch.records[0].directional_bias is DirectionalBias.LONG
    assert batch.records[0].model_version == "sentiment-rules-v1"
    assert batch.records[1].relevance is RelevanceLabel.NOISE
    assert batch.records[1].later_return == pytest.approx(0.01)


def test_adapter_uses_selected_four_hour_horizon() -> None:
    provider = make_provider(
        service=make_service(
            [
                make_candle(EVENT_TIME, close_price=100.0),
                make_candle(EVENT_TIME + timedelta(hours=4), close_price=98.0),
            ]
        )
    )

    batch = provider.get_quality_inputs(
        "workspace-alpha",
        "draft-run-fixed",
        FOUR_HOURS,
    )

    assert batch.records[0].later_return == pytest.approx(-0.02)
    assert batch.records[0].realized_direction is RealizedDirection.DOWN


def test_adapter_missing_candle_leaves_null_movement_with_warning() -> None:
    provider = make_provider(
        service=make_service([make_candle(EVENT_TIME, close_price=100.0)])
    )

    batch = provider.get_quality_inputs(
        "workspace-alpha",
        "draft-run-fixed",
        ONE_MINUTE,
    )

    assert batch.records[0].later_return is None
    assert batch.records[0].realized_direction is None
    assert any("horizon price candle" in warning for warning in batch.extra_warnings)


def test_adapter_provider_failure_leaves_null_movement_with_warning() -> None:
    service = PriceEnrichmentService(
        candle_repository=InMemoryPriceCandleRepository(),
        price_provider=FailingPriceProvider(),
    )
    provider = make_provider(service=service)

    batch = provider.get_quality_inputs(
        "workspace-alpha",
        "draft-run-fixed",
        ONE_MINUTE,
    )

    assert batch.records[0].later_return is None
    assert batch.records[0].realized_direction is None
    assert any("provider was unavailable" in warning for warning in batch.extra_warnings)
    assert any("could not be fetched" in warning for warning in batch.extra_warnings)


def test_adapter_preserves_noise_and_irrelevant_records_during_enrichment() -> None:
    records = [
        make_record(1, relevance=RelevanceLabel.RELEVANT),
        make_record(2, relevance=RelevanceLabel.NOISE, directional_bias=DirectionalBias.FLAT),
        make_record(3, relevance=RelevanceLabel.IRRELEVANT),
    ]
    provider = make_provider(repository=make_repository(records))

    batch = provider.get_quality_inputs(
        "workspace-alpha",
        "draft-run-fixed",
        ONE_MINUTE,
    )

    assert [record.relevance for record in batch.records] == [
        RelevanceLabel.RELEVANT,
        RelevanceLabel.NOISE,
        RelevanceLabel.IRRELEVANT,
    ]
    assert all(record.later_return == pytest.approx(0.01) for record in batch.records)


def test_quality_route_reads_completed_dataset_and_reports_enriched_movement() -> None:
    repository = make_repository()
    app.dependency_overrides[get_quality_input_provider] = lambda: make_provider(
        repository=repository
    )
    client = TestClient(app)

    response = client.get(
        "/api/workspaces/workspace-alpha/backtests/draft-run-fixed/quality"
        "?horizon_value=1&horizon_unit=minutes"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["workspace_id"] == "workspace-alpha"
    assert data["run_id"] == "draft-run-fixed"
    assert data["model_version"] == "sentiment-rules-v1"
    assert data["config_version"] == "news-sentiment-policy-v1"
    assert data["metrics"]["missing_movement_count"] == 0
    assert data["metrics"]["noise_count"] == 1
    assert data["representative_records"][0]["later_return"] == pytest.approx(0.01)
    assert data["representative_records"][0]["realized_direction"] == "UP"


def test_adapter_isolates_workspace_and_run() -> None:
    provider = make_provider()

    with pytest.raises(QualityRunNotFoundError):
        provider.get_quality_inputs("workspace-beta", "draft-run-fixed", ONE_MINUTE)

    with pytest.raises(QualityRunNotFoundError):
        provider.get_quality_inputs("workspace-alpha", "other-run", ONE_MINUTE)


def test_adapter_rejects_incomplete_or_provider_limited_runs() -> None:
    repository = InMemoryCompletedDatasetRepository()
    repository.save_run(
        make_summary(
            status=DatasetRunStatus.FAILED_PROVIDER_LIMITATION,
            record_count=0,
            relevant_count=0,
            noise_count=0,
            provider_limitation=DatasetProviderLimitation(
                provider_name="Sharpe Terminal",
                reason="missing provider configuration",
            ),
        ),
        [],
    )
    provider = make_provider(repository=repository)

    with pytest.raises(QualityRunIncompleteError, match="completed BACKTEST dataset"):
        provider.get_quality_inputs("workspace-alpha", "draft-run-fixed", ONE_MINUTE)


def test_adapter_rejects_completed_empty_dataset() -> None:
    repository = InMemoryCompletedDatasetRepository()
    repository.save_run(
        make_summary(record_count=0, relevant_count=0, noise_count=0),
        [],
    )
    provider = make_provider(repository=repository)

    with pytest.raises(QualityRunIncompleteError, match="no records"):
        provider.get_quality_inputs("workspace-alpha", "draft-run-fixed", ONE_MINUTE)
