from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from urllib.parse import parse_qs, urlparse

import pytest

from quantitative_sentiment_analysis.backtest_dataset.cryptopanic import (
    CRYPTOPANIC_API_KEY_ENV,
    CryptoPanicClient,
)
from quantitative_sentiment_analysis.backtest_dataset.provider import (
    DatasetProviderConfigurationError,
    DatasetProviderLimitationError,
    DatasetProviderUnavailableError,
    DatasetProviderUnsupportedScopeError,
    FixtureNewsProvider,
    ProviderFetchRequest,
)
from quantitative_sentiment_analysis.contracts import Instrument, RunMode

TIMEFRAME_START = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TIMEFRAME_END = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def make_request(**overrides: object) -> ProviderFetchRequest:
    payload: dict[str, object] = {
        "workspace_id": "workspace-alpha",
        "run_id": "draft-run-000001",
        "instrument": Instrument.BTCUSD,
        "mode": RunMode.BACKTEST,
        "timeframe_start": TIMEFRAME_START,
        "timeframe_end": TIMEFRAME_END,
    }
    payload.update(overrides)
    return ProviderFetchRequest(**payload)  # type: ignore[arg-type]


def test_fixture_provider_returns_copied_records_without_live_network() -> None:
    original = [{"id": 1, "title": "Bitcoin ETF approval"}]
    provider = FixtureNewsProvider(original)
    original[0]["title"] = "mutated"

    first = provider.fetch_historical_news(make_request())
    second = provider.fetch_historical_news(make_request())

    assert provider.provider_name == "FixtureNews"
    assert first == ({"id": 1, "title": "Bitcoin ETF approval"},)
    assert second == first
    assert first is not second


def test_provider_request_rejects_unsupported_scope() -> None:
    with pytest.raises(DatasetProviderUnsupportedScopeError):
        make_request(instrument=cast(Instrument, "ETHUSD"))

    with pytest.raises(DatasetProviderUnsupportedScopeError):
        make_request(mode=cast(RunMode, "LIVE"))


def test_cryptopanic_from_environment_requires_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(CRYPTOPANIC_API_KEY_ENV, raising=False)

    with pytest.raises(DatasetProviderConfigurationError, match=CRYPTOPANIC_API_KEY_ENV):
        CryptoPanicClient.from_environment()


def test_cryptopanic_missing_token_is_typed_provider_limitation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(CRYPTOPANIC_API_KEY_ENV, raising=False)
    client = CryptoPanicClient(auth_token=None)

    with pytest.raises(DatasetProviderLimitationError) as exc_info:
        client.fetch_historical_news(make_request())

    limitation = exc_info.value.to_schema()
    assert limitation.provider_name == "CryptoPanic"
    assert limitation.reason == "missing provider configuration"
    assert CRYPTOPANIC_API_KEY_ENV in (limitation.detail or "")


def test_cryptopanic_fetch_uses_stubbed_http_and_filters_non_record_results() -> None:
    requested_urls: list[str] = []

    def fetch_json(url: str) -> dict[str, object]:
        requested_urls.append(url)
        return {
            "results": [
                {"id": 1, "title": "Bitcoin ETF approval"},
                "unexpected",
                {"id": 2, "title": "BTC selloff"},
            ]
        }

    client = CryptoPanicClient(auth_token="secret-token", fetch_json=fetch_json)

    records = client.fetch_historical_news(make_request())

    assert records == (
        {"id": 1, "title": "Bitcoin ETF approval"},
        {"id": 2, "title": "BTC selloff"},
    )
    query = parse_qs(urlparse(requested_urls[0]).query)
    assert query["auth_token"] == ["secret-token"]
    assert query["currencies"] == ["BTC"]
    assert query["from"] == ["2026-06-01"]
    assert query["to"] == ["2026-06-08"]


def test_cryptopanic_unexpected_payload_is_provider_limitation() -> None:
    client = CryptoPanicClient(
        auth_token="secret-token",
        fetch_json=lambda url: {"status": "ok"},
    )

    with pytest.raises(DatasetProviderLimitationError, match="unexpected provider response"):
        client.fetch_historical_news(make_request())


def test_cryptopanic_fetch_failure_is_unavailable() -> None:
    def fail(url: str) -> dict[str, object]:
        raise OSError("network unavailable")

    client = CryptoPanicClient(auth_token="secret-token", fetch_json=fail)

    with pytest.raises(DatasetProviderUnavailableError, match="request failed"):
        client.fetch_historical_news(make_request())
