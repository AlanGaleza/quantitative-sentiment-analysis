from __future__ import annotations

import pytest
from sqlalchemy import text

from quantitative_sentiment_analysis.persistence.database import (
    DATABASE_URL_ENV,
    DatabaseConfigurationError,
    configured_database_url,
    get_session_factory,
    normalize_database_url,
    reset_database_state_for_tests,
)


@pytest.fixture(autouse=True)
def reset_database_cache() -> None:
    reset_database_state_for_tests()
    yield
    reset_database_state_for_tests()


def test_configured_database_url_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)

    with pytest.raises(DatabaseConfigurationError, match=DATABASE_URL_ENV):
        configured_database_url()


@pytest.mark.parametrize(
    ("raw_url", "normalized"),
    [
        (
            "postgresql://user:pass@db.example.test:5432/qsa",
            "postgresql+psycopg://user:pass@db.example.test:5432/qsa",
        ),
        (
            "postgres://user:pass@db.example.test:5432/qsa",
            "postgresql+psycopg://user:pass@db.example.test:5432/qsa",
        ),
        (
            "postgresql+psycopg://user:pass@db.example.test:5432/qsa",
            "postgresql+psycopg://user:pass@db.example.test:5432/qsa",
        ),
        ("sqlite+pysqlite:///:memory:", "sqlite+pysqlite:///:memory:"),
    ],
)
def test_normalize_database_url_uses_psycopg_for_postgres_urls(
    raw_url: str,
    normalized: str,
) -> None:
    assert normalize_database_url(raw_url) == normalized


def test_explicit_session_factory_does_not_require_environment_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)

    session_factory = get_session_factory("sqlite+pysqlite:///:memory:")

    with session_factory() as session:
        assert session.execute(text("select 1")).scalar_one() == 1
