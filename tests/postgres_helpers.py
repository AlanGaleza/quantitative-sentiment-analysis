from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.auth.security import AUTH_SECRET_ENV, hash_password
from quantitative_sentiment_analysis.persistence.database import (
    DATABASE_URL_ENV,
    create_session_factory,
    get_database_session,
    get_engine,
    reset_database_state_for_tests,
)
from quantitative_sentiment_analysis.persistence.models import (
    BacktestConfigModel,
    BacktestRunModel,
    DatasetRecordModel,
    DatasetRunModel,
    PriceCandleModel,
    SessionModel,
    UserModel,
    WorkspaceModel,
)

FRONTEND_ORIGIN = "https://frontend.example.test"
AUTH_SECRET = "test-auth-secret-value-with-at-least-32-characters"
DEFAULT_EMAIL = "trader@example.test"
DEFAULT_PASSWORD = "correct-password"


def postgres_engine_or_skip(monkeypatch: pytest.MonkeyPatch) -> Engine:
    database_url = _database_url_or_skip()
    monkeypatch.setenv(AUTH_SECRET_ENV, AUTH_SECRET)
    reset_database_state_for_tests()
    engine = get_engine(database_url)
    try:
        with engine.connect():
            pass
    except (OSError, SQLAlchemyError) as exc:
        engine.dispose()
        reset_database_state_for_tests()
        pytest.skip(f"{DATABASE_URL_ENV} is not reachable: {exc}")
    return engine


def override_database_session(app: FastAPI, engine: Engine) -> None:
    session_factory = create_session_factory(engine)

    def database_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = database_session


def clear_database(session: Session) -> None:
    session.execute(delete(PriceCandleModel))
    session.execute(delete(DatasetRecordModel))
    session.execute(delete(DatasetRunModel))
    session.execute(delete(BacktestRunModel))
    session.execute(delete(BacktestConfigModel))
    session.execute(delete(SessionModel))
    session.execute(delete(WorkspaceModel))
    session.execute(delete(UserModel))
    session.commit()


def seed_user_with_workspace(
    session: Session,
    *,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
    workspace_slug: str = "workspace-alpha",
    workspace_name: str = "Workspace Alpha",
) -> tuple[UserModel, WorkspaceModel]:
    user = UserModel(
        email=email,
        password_hash=hash_password(password),
        disabled=False,
    )
    session.add(user)
    session.flush()
    workspace = WorkspaceModel(
        slug=workspace_slug,
        owner_user_id=user.id,
        name=workspace_name,
    )
    session.add(workspace)
    session.commit()
    session.refresh(user)
    session.refresh(workspace)
    return user, workspace


def login(
    client: TestClient,
    *,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert response.status_code == 200


def _database_url_or_skip() -> str:
    import os

    database_url = os.getenv(DATABASE_URL_ENV, "").strip()
    if not database_url:
        pytest.skip(f"{DATABASE_URL_ENV} is required for Postgres integration tests")
    return database_url
