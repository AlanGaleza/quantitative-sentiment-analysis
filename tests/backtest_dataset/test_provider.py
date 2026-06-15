from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import cast
from urllib.parse import parse_qs, urlparse

import pytest

from quantitative_sentiment_analysis.backtest_dataset.sharpe import (
    SHARPE_API_KEY_ENV,
    SHARPE_NEWS_API_URL,
    SharpeTerminalClient,
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


def test_sharpe_from_environment_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SHARPE_API_KEY_ENV, raising=False)

    with pytest.raises(DatasetProviderConfigurationError, match=SHARPE_API_KEY_ENV):
        SharpeTerminalClient.from_environment()


def test_sharpe_missing_api_key_is_typed_provider_limitation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(SHARPE_API_KEY_ENV, raising=False)
    client = SharpeTerminalClient(api_key=None)

    with pytest.raises(DatasetProviderLimitationError) as exc_info:
        client.fetch_historical_news(make_request())

    limitation = exc_info.value.to_schema()
    assert limitation.provider_name == "Sharpe Terminal"
    assert limitation.reason == "missing provider configuration"
    assert SHARPE_API_KEY_ENV in (limitation.detail or "")


def test_sharpe_fetch_uses_bearer_auth_and_filters_to_requested_window() -> None:
    requested: list[tuple[str, dict[str, str]]] = []

    def fetch_json(url: str, headers: Mapping[str, str]) -> dict[str, object]:
        requested.append((url, dict(headers)))
        return {
            "data": {
                "articles": [
                    {
                        "id": "sharpe-1",
                        "title": "Bitcoin ETF approval",
                        "summary": "BTC spot inflows accelerate.",
                        "source": "Sharpe News",
                        "published": "2026-06-02T09:00:00Z",
                        "category": "crypto",
                        "coin": "BTC",
                        "url": "https://example.test/sharpe-1",
                    },
                    {
                        "id": "future",
                        "title": "BTC headline outside requested window",
                        "source": "Sharpe News",
                        "published": "2026-06-09T09:00:00Z",
                    },
                    {
                        "id": "sharpe-2",
                        "title": "BTC selloff",
                        "source": {"id": "terminal", "name": "Sharpe Terminal"},
                        "published": "2026-06-08T12:00:00Z",
                    },
                    "unexpected",
                ]
            }
        }

    client = SharpeTerminalClient(
        api_key="secret-token",
        fetch_json=fetch_json,
        page_limit=100,
    )

    records = client.fetch_historical_news(make_request())

    assert records == (
        {
            "id": "sharpe-1",
            "published_at": "2026-06-02T09:00:00Z",
            "title": "Bitcoin ETF approval",
            "body": "BTC spot inflows accelerate.",
            "source_id": "Sharpe News",
            "source_name": "Sharpe News",
            "url": "https://example.test/sharpe-1",
            "category": "crypto",
            "coin": "BTC",
        },
        {
            "id": "sharpe-2",
            "published_at": "2026-06-08T12:00:00Z",
            "title": "BTC selloff",
            "body": None,
            "source_id": "terminal",
            "source_name": "Sharpe Terminal",
            "url": None,
            "category": None,
            "coin": None,
        },
    )
    url, headers = requested[0]
    assert headers["Authorization"] == "Bearer secret-token"
    assert headers["Accept"] == "application/json"
    assert url.startswith(f"{SHARPE_NEWS_API_URL}?")
    query = parse_qs(urlparse(url).query)
    assert query["limit"] == ["100"]
    assert query["offset"] == ["0"]
    assert query["category"] == ["crypto"]
    assert query["coin"] == ["BTC"]
    assert query["since"] == ["2026-06-01T12:00:00Z"]


def test_sharpe_fetch_paginates_until_short_article_page() -> None:
    requested_offsets: list[str] = []

    def fetch_json(url: str, headers: Mapping[str, str]) -> dict[str, object]:
        query = parse_qs(urlparse(url).query)
        requested_offsets.append(query["offset"][0])
        if query["offset"] == ["0"]:
            return {
                "data": {
                    "articles": [
                        {
                            "id": "sharpe-1",
                            "title": "Bitcoin ETF approval",
                            "source": "Sharpe News",
                            "published": "2026-06-02T09:00:00Z",
                        }
                    ]
                }
            }
        return {"data": {"articles": []}}

    client = SharpeTerminalClient(
        api_key="secret-token",
        fetch_json=fetch_json,
        page_limit=1,
    )

    records = client.fetch_historical_news(make_request())

    assert requested_offsets == ["0", "1"]
    assert [record["id"] for record in records] == ["sharpe-1"]


def test_sharpe_fetch_filters_non_record_results() -> None:
    def fetch_json(url: str, headers: Mapping[str, str]) -> dict[str, object]:
        return {
            "data": {
                "articles": [
                    {"id": 1, "title": "Bitcoin ETF approval"},
                    "unexpected",
                    {"id": 2, "title": "BTC selloff"},
                ]
            }
        }

    client = SharpeTerminalClient(api_key="secret-token", fetch_json=fetch_json)

    records = client.fetch_historical_news(make_request())

    assert records == (
        {
            "id": 1,
            "published_at": None,
            "title": "Bitcoin ETF approval",
            "body": None,
            "source_id": None,
            "source_name": None,
            "url": None,
            "category": None,
            "coin": None,
        },
        {
            "id": 2,
            "published_at": None,
            "title": "BTC selloff",
            "body": None,
            "source_id": None,
            "source_name": None,
            "url": None,
            "category": None,
            "coin": None,
        },
    )


def test_sharpe_unexpected_payload_is_provider_limitation() -> None:
    client = SharpeTerminalClient(
        api_key="secret-token",
        fetch_json=lambda url, headers: {"status": "ok"},
    )

    with pytest.raises(DatasetProviderLimitationError, match="unexpected provider response"):
        client.fetch_historical_news(make_request())


def test_sharpe_fetch_failure_is_unavailable() -> None:
    def fail(url: str, headers: Mapping[str, str]) -> dict[str, object]:
        raise OSError("network unavailable")

    client = SharpeTerminalClient(api_key="secret-token", fetch_json=fail)

    with pytest.raises(DatasetProviderUnavailableError, match="request failed"):
        client.fetch_historical_news(make_request())
