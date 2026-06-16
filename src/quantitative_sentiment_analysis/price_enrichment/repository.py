from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime
from quantitative_sentiment_analysis.persistence.models import PriceCandleModel
from quantitative_sentiment_analysis.price_enrichment.schemas import PriceCandle

_UPSERT_BATCH_SIZE = 1000


class PriceCandleRepository(Protocol):
    """Storage boundary for deterministic historical price candle cache."""

    def upsert_candles(self, candles: Iterable[PriceCandle]) -> tuple[PriceCandle, ...]:
        """Store candles idempotently and return the stored candle domain objects."""
        ...

    def list_candles(
        self,
        *,
        provider_name: str,
        symbol: str,
        interval: str,
        start_open_time: datetime,
        end_open_time: datetime,
    ) -> tuple[PriceCandle, ...]:
        """Return cached candles in an inclusive open-time range."""
        ...

    def get_candles_by_open_time(
        self,
        *,
        provider_name: str,
        symbol: str,
        interval: str,
        open_times: Iterable[datetime],
    ) -> dict[datetime, PriceCandle]:
        """Return cached candles for exact open times keyed by UTC open time."""
        ...


class PostgresPriceCandleRepository:
    """Postgres-backed cache for provider historical price candles."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_candles(self, candles: Iterable[PriceCandle]) -> tuple[PriceCandle, ...]:
        stored_candles = tuple(_validated_candle(candle) for candle in candles)
        if not stored_candles:
            return ()

        try:
            for candle_batch in _batched(stored_candles, _UPSERT_BATCH_SIZE):
                statement = insert(PriceCandleModel).values(
                    [_candle_to_row(candle) for candle in candle_batch]
                )
                upsert = statement.on_conflict_do_update(
                    constraint="uq_price_candles_provider_symbol_interval_open",
                    set_={
                        "close_time": statement.excluded.close_time,
                        "open_price": statement.excluded.open_price,
                        "high_price": statement.excluded.high_price,
                        "low_price": statement.excluded.low_price,
                        "close_price": statement.excluded.close_price,
                        "volume": statement.excluded.volume,
                        "quote_volume": statement.excluded.quote_volume,
                        "provider_metadata": statement.excluded.provider_metadata,
                    },
                )
                self._session.execute(upsert)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        provider_name = stored_candles[0].provider_name
        symbol = stored_candles[0].symbol
        interval = stored_candles[0].interval
        open_times = [candle.open_time for candle in stored_candles]
        return tuple(
            self.get_candles_by_open_time(
                provider_name=provider_name,
                symbol=symbol,
                interval=interval,
                open_times=open_times,
            ).values()
        )

    def list_candles(
        self,
        *,
        provider_name: str,
        symbol: str,
        interval: str,
        start_open_time: datetime,
        end_open_time: datetime,
    ) -> tuple[PriceCandle, ...]:
        start = _utc_datetime(start_open_time)
        end = _utc_datetime(end_open_time)
        if end < start:
            raise ValueError("end_open_time must be greater than or equal to start_open_time")

        rows = self._session.scalars(
            select(PriceCandleModel)
            .where(
                PriceCandleModel.provider_name == provider_name,
                PriceCandleModel.symbol == symbol,
                PriceCandleModel.interval == interval,
                PriceCandleModel.open_time >= start,
                PriceCandleModel.open_time <= end,
            )
            .order_by(PriceCandleModel.open_time)
        )
        return tuple(_candle_from_model(row) for row in rows)

    def get_candles_by_open_time(
        self,
        *,
        provider_name: str,
        symbol: str,
        interval: str,
        open_times: Iterable[datetime],
    ) -> dict[datetime, PriceCandle]:
        normalized_open_times = tuple(sorted({_utc_datetime(value) for value in open_times}))
        if not normalized_open_times:
            return {}

        rows = self._session.scalars(
            select(PriceCandleModel)
            .where(
                PriceCandleModel.provider_name == provider_name,
                PriceCandleModel.symbol == symbol,
                PriceCandleModel.interval == interval,
                PriceCandleModel.open_time.in_(normalized_open_times),
            )
            .order_by(PriceCandleModel.open_time)
        )
        return {
            candle.open_time: candle
            for candle in (_candle_from_model(row) for row in rows)
        }


def _candle_to_row(candle: PriceCandle) -> dict[str, object]:
    return {
        "provider_name": candle.provider_name,
        "symbol": candle.symbol,
        "interval": candle.interval,
        "open_time": candle.open_time,
        "close_time": candle.close_time,
        "open_price": candle.open_price,
        "high_price": candle.high_price,
        "low_price": candle.low_price,
        "close_price": candle.close_price,
        "volume": None,
        "quote_volume": None,
        "provider_metadata": None,
    }


def _batched(
    candles: Sequence[PriceCandle],
    batch_size: int,
) -> Iterator[Sequence[PriceCandle]]:
    for index in range(0, len(candles), batch_size):
        yield candles[index : index + batch_size]


def _validated_candle(candle: PriceCandle) -> PriceCandle:
    return PriceCandle.model_validate(candle.model_dump())


def _candle_from_model(row: PriceCandleModel) -> PriceCandle:
    return PriceCandle.model_validate(
        {
            "provider_name": row.provider_name,
            "symbol": row.symbol,
            "interval": row.interval,
            "open_time": row.open_time,
            "close_time": row.close_time,
            "open_price": row.open_price,
            "high_price": row.high_price,
            "low_price": row.low_price,
            "close_price": row.close_price,
        }
    )


def _utc_datetime(value: datetime) -> datetime:
    return require_aware_datetime(value).astimezone(UTC)
