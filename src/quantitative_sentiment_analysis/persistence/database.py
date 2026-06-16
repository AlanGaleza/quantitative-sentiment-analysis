from __future__ import annotations

import os
from collections.abc import Generator, Mapping

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL_ENV = "DATABASE_URL"


class DatabaseConfigurationError(RuntimeError):
    """Raised when durable persistence is requested without database settings."""


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configured_database_url(env: Mapping[str, str] | None = None) -> str:
    source = env if env is not None else os.environ
    raw_url = source.get(DATABASE_URL_ENV, "").strip()
    if not raw_url:
        raise DatabaseConfigurationError(
            f"{DATABASE_URL_ENV} is required for Postgres-backed persistence"
        )
    return normalize_database_url(raw_url)


def normalize_database_url(url: str) -> str:
    stripped = url.strip()
    if stripped.startswith("postgresql+psycopg://"):
        return stripped
    if stripped.startswith("postgresql://"):
        return f"postgresql+psycopg://{stripped.removeprefix('postgresql://')}"
    if stripped.startswith("postgres://"):
        return f"postgresql+psycopg://{stripped.removeprefix('postgres://')}"
    return stripped


def get_engine(database_url: str | None = None) -> Engine:
    if database_url is not None:
        return create_engine(normalize_database_url(database_url), pool_pre_ping=True)

    global _engine
    if _engine is None:
        _engine = create_engine(configured_database_url(), pool_pre_ping=True)
    return _engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def get_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    if database_url is not None:
        return create_session_factory(get_engine(database_url))

    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


def get_database_session() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    with session_factory() as session:
        yield session


def reset_database_state_for_tests() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
