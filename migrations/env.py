from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from quantitative_sentiment_analysis.persistence.database import (
    DATABASE_URL_ENV,
    normalize_database_url,
)
from quantitative_sentiment_analysis.persistence.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def database_url_from_environment() -> str:
    env_url = os.getenv(DATABASE_URL_ENV, "").strip()
    ini_url = config.get_main_option("sqlalchemy.url", "").strip()
    database_url = env_url or ini_url
    if not database_url:
        raise RuntimeError(
            f"{DATABASE_URL_ENV} is required to run Alembic migrations"
        )
    return normalize_database_url(database_url)


def run_migrations_offline() -> None:
    context.configure(
        url=database_url_from_environment(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url_from_environment()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
