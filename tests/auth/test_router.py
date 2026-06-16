from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.auth.repository import AuthRepository
from quantitative_sentiment_analysis.auth.security import (
    AUTH_SECRET_ENV,
    QSA_SESSION_COOKIE_SECURE,
    hash_password,
    token_digest,
)
from quantitative_sentiment_analysis.main import create_app
from quantitative_sentiment_analysis.persistence.database import (
    DATABASE_URL_ENV,
    create_session_factory,
    get_database_session,
    get_engine,
    reset_database_state_for_tests,
)
from quantitative_sentiment_analysis.persistence.models import (
    SessionModel,
    UserModel,
    WorkspaceModel,
)

AUTH_SECRET = "test-auth-secret-value-for-router-checks"
FRONTEND_ORIGIN = "https://frontend.example.test"


@pytest.fixture()
def engine() -> Generator[Engine, None, None]:
    database_url = os.getenv(DATABASE_URL_ENV, "").strip()
    if not database_url:
        pytest.skip(f"{DATABASE_URL_ENV} is required for auth router integration tests")
    reset_database_state_for_tests()
    engine = get_engine(database_url)
    yield engine
    engine.dispose()
    reset_database_state_for_tests()


@pytest.fixture()
def db_session(engine: Engine) -> Generator[Session, None, None]:
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        _clear_auth_tables(session)
        yield session
        _clear_auth_tables(session)


@pytest.fixture()
def client(
    monkeypatch: pytest.MonkeyPatch,
    engine: Engine,
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv(AUTH_SECRET_ENV, AUTH_SECRET)
    monkeypatch.delenv(QSA_SESSION_COOKIE_SECURE, raising=False)
    session_factory = create_session_factory(engine)

    def override_database_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    test_app = create_app(cors_allowed_origins=[FRONTEND_ORIGIN])
    test_app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(test_app, base_url="https://api.example.test") as test_client:
        yield test_client
    test_app.dependency_overrides.clear()


def test_login_sets_httponly_cookie_and_me_bootstraps_current_user(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_user_with_workspace(db_session)

    response = client.post(
        "/api/auth/login",
        json={"email": " Trader@Example.TEST ", "password": "correct-password"},
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]
    assert "SameSite=none" in response.headers["set-cookie"]
    data = response.json()
    assert data["user"]["email"] == "trader@example.test"
    assert data["workspaces"][0]["slug"] == "demo-workspace"
    assert data["default_workspace_slug"] == "demo-workspace"
    assert "token" not in str(data).lower()

    me_response = client.get("/api/auth/me")

    assert me_response.status_code == 200
    assert me_response.json() == data


def test_login_rejects_invalid_credentials_with_generic_401(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_user_with_workspace(db_session)

    response = client.post(
        "/api/auth/login",
        json={"email": "trader@example.test", "password": "wrong-password"},
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid email or password"
    assert "set-cookie" not in response.headers


def test_logout_revokes_session_and_clears_cookie(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_user_with_workspace(db_session)
    login_response = client.post(
        "/api/auth/login",
        json={"email": "trader@example.test", "password": "correct-password"},
        headers={"Origin": FRONTEND_ORIGIN},
    )
    assert login_response.status_code == 200

    logout_response = client.post(
        "/api/auth/logout",
        headers={"Origin": FRONTEND_ORIGIN},
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {"status": "ok"}
    assert "Max-Age=0" in logout_response.headers["set-cookie"]
    assert client.get("/api/auth/me").status_code == 401

    db_session.expire_all()
    stored_session = db_session.query(SessionModel).one()
    assert stored_session.revoked_at is not None


def test_me_rejects_expired_and_revoked_sessions(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(AUTH_SECRET_ENV, AUTH_SECRET)
    user, _workspace = _create_user_with_workspace(db_session)
    expired_token = "expired-session-token"
    revoked_token = "revoked-session-token"
    db_session.add_all(
        [
            SessionModel(
                token_hash=token_digest(expired_token),
                user_id=user.id,
                expires_at=datetime.now(UTC) - timedelta(seconds=1),
            ),
            SessionModel(
                token_hash=token_digest(revoked_token),
                user_id=user.id,
                expires_at=datetime.now(UTC) + timedelta(days=1),
                revoked_at=datetime.now(UTC),
            ),
        ]
    )
    db_session.commit()

    client.cookies.set("qsa_session", expired_token, domain="api.example.test")
    assert client.get("/api/auth/me").status_code == 401

    client.cookies.set("qsa_session", revoked_token, domain="api.example.test")
    assert client.get("/api/auth/me").status_code == 401


def test_owned_workspace_dependency_returns_404_for_cross_owned_workspace(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(AUTH_SECRET_ENV, AUTH_SECRET)
    user, _workspace = _create_user_with_workspace(db_session)
    other_user = UserModel(
        email="other@example.test",
        password_hash=hash_password("other-password"),
        disabled=False,
    )
    db_session.add(other_user)
    db_session.flush()
    db_session.add(
        WorkspaceModel(
            slug="other-workspace",
            owner_user_id=other_user.id,
            name="Other Workspace",
        )
    )
    db_session.commit()

    repository = AuthRepository(db_session)

    assert (
        repository.get_owned_workspace(
            user_id=user.id,
            workspace_slug="demo-workspace",
        )
        is not None
    )
    assert (
        repository.get_owned_workspace(
            user_id=user.id,
            workspace_slug="other-workspace",
        )
        is None
    )


def _create_user_with_workspace(
    session: Session,
) -> tuple[UserModel, WorkspaceModel]:
    user = UserModel(
        email="trader@example.test",
        password_hash=hash_password("correct-password"),
        disabled=False,
    )
    session.add(user)
    session.flush()
    workspace = WorkspaceModel(
        slug="demo-workspace",
        owner_user_id=user.id,
        name="Demo Workspace",
    )
    session.add(workspace)
    session.commit()
    session.refresh(user)
    session.refresh(workspace)
    return user, workspace


def _clear_auth_tables(session: Session) -> None:
    session.execute(delete(SessionModel))
    session.execute(delete(WorkspaceModel))
    session.execute(delete(UserModel))
    session.commit()
