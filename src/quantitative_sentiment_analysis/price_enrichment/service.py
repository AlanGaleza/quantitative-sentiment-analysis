from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

from quantitative_sentiment_analysis.backtest_quality.schemas import (
    QualityHorizon,
    QualityInputBatch,
    QualityInputRecord,
)
from quantitative_sentiment_analysis.contracts import DatasetRecord, Instrument, RunMode
from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime
from quantitative_sentiment_analysis.price_enrichment.movement import (
    compute_price_movement,
    required_candle_open_times,
)
from quantitative_sentiment_analysis.price_enrichment.provider import (
    PRICE_INTERVAL_1M,
    PRICE_PROXY_SYMBOL,
    HistoricalPriceProvider,
    PriceFetchRequest,
    PriceProviderConfigurationError,
    PriceProviderError,
    PriceProviderLimitationError,
    PriceProviderUnavailableError,
)
from quantitative_sentiment_analysis.price_enrichment.repository import (
    PriceCandleRepository,
)
from quantitative_sentiment_analysis.price_enrichment.schemas import (
    PriceCandle,
    PriceMissingReason,
)

_ONE_MINUTE = timedelta(minutes=1)


class PriceEnrichmentService:
    """Coordinates cached/live candles and quality movement enrichment."""

    def __init__(
        self,
        *,
        candle_repository: PriceCandleRepository,
        price_provider: HistoricalPriceProvider,
    ) -> None:
        self._candle_repository = candle_repository
        self._price_provider = price_provider

    def enrich_quality_inputs(
        self,
        *,
        records: Sequence[DatasetRecord],
        horizon: QualityHorizon,
        run_timeframe_start: datetime,
        run_timeframe_end: datetime,
    ) -> QualityInputBatch:
        timeframe_start = require_aware_datetime(run_timeframe_start).astimezone(UTC)
        timeframe_end = require_aware_datetime(run_timeframe_end).astimezone(UTC)
        if timeframe_end < timeframe_start:
            raise ValueError(
                "run_timeframe_end must be greater than or equal to run_timeframe_start"
            )

        ordered_records = tuple(records)
        required_open_times = required_candle_open_times(
            (record.timestamp for record in ordered_records),
            horizon,
        )
        warnings: list[str] = []
        candles_by_open_time = self._read_cached_candles(
            required_open_times,
            warnings=warnings,
        )
        missing_open_times = tuple(
            open_time
            for open_time in required_open_times
            if open_time not in candles_by_open_time
        )

        if missing_open_times:
            fetched_candles = self._fetch_missing_candles(
                missing_open_times,
                run_timeframe_start=timeframe_start,
                run_timeframe_end=timeframe_end,
                warnings=warnings,
            )
            for candle in fetched_candles:
                candles_by_open_time[candle.open_time] = candle
            self._upsert_fetched_candles(fetched_candles, warnings=warnings)

        quality_records: list[QualityInputRecord] = []
        missing_reasons: Counter[PriceMissingReason] = Counter()
        for record in ordered_records:
            movement = compute_price_movement(
                event_timestamp=record.timestamp,
                horizon=horizon,
                candles_by_open_time=candles_by_open_time,
            )
            if movement.missing_reason is not None:
                missing_reasons[movement.missing_reason] += 1
            quality_records.append(
                QualityInputRecord(
                    workspace_id=record.workspace_id,
                    run_id=record.run_id,
                    record_id=record.record_id,
                    instrument=record.instrument.value,
                    mode=record.mode.value,
                    event_timestamp=record.timestamp,
                    headline=record.headline,
                    source_id=record.source_id,
                    source_name=record.source_name,
                    sentiment_score=record.sentiment_score,
                    directional_bias=record.directional_bias,
                    confidence=record.confidence,
                    relevance=record.relevance,
                    later_return=movement.later_return,
                    realized_direction=movement.realized_direction,
                    model_version=record.model_version,
                    config_version=record.config_version,
                )
            )

        warnings.extend(_missing_reason_warnings(missing_reasons))
        return QualityInputBatch(
            records=tuple(quality_records),
            extra_warnings=tuple(_dedupe_preserving_order(warnings)),
        )

    def _read_cached_candles(
        self,
        open_times: Iterable[datetime],
        *,
        warnings: list[str],
    ) -> dict[datetime, PriceCandle]:
        try:
            return self._candle_repository.get_candles_by_open_time(
                provider_name=self._price_provider.provider_name,
                symbol=PRICE_PROXY_SYMBOL,
                interval=PRICE_INTERVAL_1M,
                open_times=open_times,
            )
        except Exception as exc:
            warnings.append(
                "Price candle cache read failed; price movement remains partial "
                f"for this report. Detail: {exc}"
            )
            return {}

    def _fetch_missing_candles(
        self,
        missing_open_times: Sequence[datetime],
        *,
        run_timeframe_start: datetime,
        run_timeframe_end: datetime,
        warnings: list[str],
    ) -> tuple[PriceCandle, ...]:
        fetched: list[PriceCandle] = []
        failed_window_count = 0
        for start_open_time, end_open_time in _contiguous_windows(missing_open_times):
            request = PriceFetchRequest(
                instrument=Instrument.BTCUSD,
                mode=RunMode.BACKTEST,
                timeframe_start=start_open_time,
                timeframe_end=end_open_time,
                provider_metadata={
                    "proxy": "BTCUSD via Binance Spot BTCUSDT",
                    "run_timeframe_start": run_timeframe_start.isoformat(),
                    "run_timeframe_end": run_timeframe_end.isoformat(),
                },
            )
            try:
                fetched.extend(self._price_provider.fetch_price_candles(request))
            except PriceProviderConfigurationError as exc:
                failed_window_count += 1
                warnings.append(
                    "Price provider configuration failed; price movement remains "
                    f"partial. Detail: {exc}"
                )
            except PriceProviderUnavailableError as exc:
                failed_window_count += 1
                warnings.append(
                    "Price provider was unavailable; price movement remains partial. "
                    f"Detail: {exc}"
                )
            except PriceProviderLimitationError as exc:
                failed_window_count += 1
                warnings.append(
                    "Price provider returned unusable candle data; price movement "
                    f"remains partial. Detail: {exc}"
                )
            except PriceProviderError as exc:
                failed_window_count += 1
                warnings.append(
                    "Price provider failed; price movement remains partial. "
                    f"Detail: {exc}"
                )
        if failed_window_count:
            warnings.append(
                f"{failed_window_count} missing price candle window(s) could not be "
                "fetched from the configured provider."
            )
        return tuple(sorted(fetched, key=lambda candle: candle.open_time))

    def _upsert_fetched_candles(
        self,
        candles: Sequence[PriceCandle],
        *,
        warnings: list[str],
    ) -> None:
        if not candles:
            return
        try:
            self._candle_repository.upsert_candles(candles)
        except Exception as exc:
            warnings.append(
                "Price candle cache write failed; fetched candles were used only "
                f"for this report. Detail: {exc}"
            )


def _contiguous_windows(
    open_times: Sequence[datetime],
) -> tuple[tuple[datetime, datetime], ...]:
    sorted_open_times = tuple(sorted(set(open_times)))
    if not sorted_open_times:
        return ()

    windows: list[tuple[datetime, datetime]] = []
    start = sorted_open_times[0]
    previous = start
    for open_time in sorted_open_times[1:]:
        if open_time - previous == _ONE_MINUTE:
            previous = open_time
            continue
        windows.append((start, previous))
        start = open_time
        previous = open_time
    windows.append((start, previous))
    return tuple(windows)


def _missing_reason_warnings(
    missing_reasons: Counter[PriceMissingReason],
) -> tuple[str, ...]:
    warning_by_reason = {
        PriceMissingReason.MISSING_EVENT_CANDLE: (
            "record(s) missing price movement because the event price candle was "
            "unavailable."
        ),
        PriceMissingReason.MISSING_HORIZON_CANDLE: (
            "record(s) missing price movement because the horizon price candle was "
            "unavailable."
        ),
        PriceMissingReason.INVALID_EVENT_PRICE: (
            "record(s) missing price movement because the event close price was "
            "invalid."
        ),
        PriceMissingReason.INVALID_HORIZON_PRICE: (
            "record(s) missing price movement because the horizon close price was "
            "invalid."
        ),
        PriceMissingReason.NON_FINITE_RETURN: (
            "record(s) missing price movement because the calculated return was "
            "non-finite."
        ),
    }
    return tuple(
        f"{missing_reasons[reason]} {warning_by_reason[reason]}"
        for reason in PriceMissingReason
        if missing_reasons[reason]
    )


def _dedupe_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)
