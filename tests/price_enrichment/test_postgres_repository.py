from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from quantitative_sentiment_analysis.persistence.database import (
    create_session_factory,
    reset_database_state_for_tests,
)
from quantitative_sentiment_analysis.persistence.models import PriceCandleModel
from quantitative_sentiment_analysis.price_enrichment import PriceCandle
from quantitative_sentiment_analysis.price_enrichment.repository import (
    PostgresPriceCandleRepository,
)
from tests.postgres_helpers import clear_database, postgres_engine_or_skip

BASE_TIME = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


@pytest.fixture()
def session_factory(monkeypatch: pytest.MonkeyPatch):
    engine = postgres_engine_or_skip(monkeypatch)
    factory = create_session_factory(engine)
    with factory() as session:
        clear_database(session)
    yield factory
    with factory() as session:
        clear_database(session)
    engine.dispose()
    reset_database_state_for_tests()


def make_candle(
    offset: int,
    *,
    provider_name: str = "FixturePrice",
    symbol: str = "BTCUSDT",
    close_price: float = 100.0,
) -> PriceCandle:
    open_time = BASE_TIME + timedelta(minutes=offset)
    return PriceCandle(
        provider_name=provider_name,
        symbol=symbol,
        interval="1m",
        open_time=open_time,
        close_time=open_time + timedelta(minutes=1),
        open_price=close_price,
        high_price=close_price,
        low_price=close_price,
        close_price=close_price,
    )


def test_postgres_price_candle_repository_upserts_and_reads_ordered_range(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = PostgresPriceCandleRepository(session)

        stored = repository.upsert_candles(
            [make_candle(2, close_price=102.0), make_candle(0, close_price=100.0)]
        )
        ranged = repository.list_candles(
            provider_name="FixturePrice",
            symbol="BTCUSDT",
            interval="1m",
            start_open_time=BASE_TIME,
            end_open_time=BASE_TIME + timedelta(minutes=2),
        )

    assert [candle.open_time for candle in stored] == [
        BASE_TIME,
        BASE_TIME + timedelta(minutes=2),
    ]
    assert [candle.close_price for candle in ranged] == [100.0, 102.0]


def test_postgres_price_candle_repository_reads_exact_open_times(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = PostgresPriceCandleRepository(session)
        repository.upsert_candles(
            [
                make_candle(0, close_price=100.0),
                make_candle(1, close_price=101.0),
                make_candle(2, close_price=102.0),
            ]
        )

        by_time = repository.get_candles_by_open_time(
            provider_name="FixturePrice",
            symbol="BTCUSDT",
            interval="1m",
            open_times=[
                BASE_TIME + timedelta(minutes=2),
                BASE_TIME,
                BASE_TIME + timedelta(minutes=2),
            ],
        )

    assert tuple(by_time) == (BASE_TIME, BASE_TIME + timedelta(minutes=2))
    assert by_time[BASE_TIME].close_price == 100.0
    assert by_time[BASE_TIME + timedelta(minutes=2)].close_price == 102.0


def test_postgres_price_candle_repository_upsert_updates_duplicate_candle(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = PostgresPriceCandleRepository(session)

        repository.upsert_candles([make_candle(0, close_price=100.0)])
        repository.upsert_candles([make_candle(0, close_price=105.0)])
        rows = session.scalars(select(PriceCandleModel)).all()
        by_time = repository.get_candles_by_open_time(
            provider_name="FixturePrice",
            symbol="BTCUSDT",
            interval="1m",
            open_times=[BASE_TIME],
        )

    assert len(rows) == 1
    assert by_time[BASE_TIME].close_price == 105.0


def test_postgres_price_candle_repository_batches_large_upserts(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = PostgresPriceCandleRepository(session)

        stored = repository.upsert_candles(
            make_candle(offset, close_price=100.0 + offset)
            for offset in range(6000)
        )
        row_count = session.scalar(select(func.count()).select_from(PriceCandleModel))

    assert row_count == 6000
    assert len(stored) == 6000
    assert stored[0].open_time == BASE_TIME
    assert stored[-1].open_time == BASE_TIME + timedelta(minutes=5999)


def test_postgres_price_candle_repository_separates_provider_symbol_and_interval(
    session_factory,
) -> None:
    with session_factory() as session:
        repository = PostgresPriceCandleRepository(session)
        repository.upsert_candles(
            [
                make_candle(0, provider_name="FixturePrice", close_price=100.0),
                make_candle(0, provider_name="OtherPrice", close_price=101.0),
                make_candle(0, symbol="ETHUSDT", close_price=102.0),
            ]
        )

        btc_fixture = repository.get_candles_by_open_time(
            provider_name="FixturePrice",
            symbol="BTCUSDT",
            interval="1m",
            open_times=[BASE_TIME],
        )

    assert len(btc_fixture) == 1
    assert btc_fixture[BASE_TIME].close_price == 100.0


def test_postgres_price_candle_repository_rejects_invalid_candle_before_storage(
    session_factory,
) -> None:
    invalid_candle = PriceCandle.model_construct(
        provider_name="FixturePrice",
        symbol="BTCUSDT",
        interval="1m",
        open_time=BASE_TIME,
        close_time=BASE_TIME + timedelta(minutes=1),
        open_price=0.0,
        high_price=0.0,
        low_price=0.0,
        close_price=0.0,
    )

    with session_factory() as session:
        repository = PostgresPriceCandleRepository(session)

        with pytest.raises(ValueError):
            repository.upsert_candles([invalid_candle])

        rows = session.scalars(select(PriceCandleModel)).all()

    assert rows == []
