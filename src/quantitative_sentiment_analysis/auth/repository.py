from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.auth.security import (
    generate_session_token,
    hash_password,
    normalize_email,
    session_ttl_seconds,
    token_digest,
    verify_password,
)
from quantitative_sentiment_analysis.persistence.models import (
    SessionModel,
    UserModel,
    WorkspaceModel,
)

Clock = Callable[[], datetime]


class AuthRepositoryError(RuntimeError):
    """Raised when auth persistence cannot satisfy a safe operation."""


class AuthRepository:
    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(UTC))

    def find_user_by_email(self, email: str) -> UserModel | None:
        return self._session.scalar(
            select(UserModel).where(UserModel.email == normalize_email(email))
        )

    def authenticate_user(self, email: str, password: str) -> UserModel | None:
        user = self.find_user_by_email(email)
        if user is None or user.disabled:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_session(self, user: UserModel) -> str:
        token = generate_session_token()
        session = SessionModel(
            token_hash=token_digest(token),
            user_id=user.id,
            expires_at=self._now() + timedelta(seconds=session_ttl_seconds()),
        )
        self._session.add(session)
        self._session.commit()
        return token

    def revoke_session(self, token: str) -> bool:
        session = self._session.scalar(
            select(SessionModel).where(SessionModel.token_hash == token_digest(token))
        )
        if session is None:
            return False
        if session.revoked_at is None:
            session.revoked_at = self._now()
            self._session.commit()
        return True

    def resolve_current_user(self, token: str) -> UserModel | None:
        session = self._session.scalar(
            select(SessionModel).where(SessionModel.token_hash == token_digest(token))
        )
        if session is None:
            return None
        if session.revoked_at is not None:
            return None
        if _aware_utc(session.expires_at) <= self._now():
            return None
        if session.user.disabled:
            return None
        return session.user

    def load_owned_workspaces(self, user_id: uuid.UUID) -> tuple[WorkspaceModel, ...]:
        return tuple(
            self._session.scalars(
                select(WorkspaceModel)
                .where(WorkspaceModel.owner_user_id == user_id)
                .order_by(WorkspaceModel.created_at, WorkspaceModel.slug)
            )
        )

    def get_owned_workspace(
        self,
        *,
        user_id: uuid.UUID,
        workspace_slug: str,
    ) -> WorkspaceModel | None:
        return self._session.scalar(
            select(WorkspaceModel).where(
                WorkspaceModel.owner_user_id == user_id,
                WorkspaceModel.slug == workspace_slug,
            )
        )

    def upsert_seed_user(
        self,
        *,
        email: str,
        password: str,
        workspace_slug: str,
        workspace_name: str,
    ) -> tuple[UserModel, WorkspaceModel]:
        normalized_email = normalize_email(email)
        normalized_slug = _require_workspace_slug(workspace_slug)
        display_name = workspace_name.strip()
        if not display_name:
            raise AuthRepositoryError("seed workspace name must not be empty")

        now = self._now()
        user = self.find_user_by_email(normalized_email)
        if user is None:
            user = UserModel(
                email=normalized_email,
                password_hash=hash_password(password),
                disabled=False,
            )
            self._session.add(user)
            self._session.flush()
        else:
            user.password_hash = hash_password(password)
            user.disabled = False
            user.updated_at = now

        workspace = self._session.scalar(
            select(WorkspaceModel).where(WorkspaceModel.slug == normalized_slug)
        )
        if workspace is None:
            workspace = WorkspaceModel(
                slug=normalized_slug,
                owner_user_id=user.id,
                name=display_name,
            )
            self._session.add(workspace)
            self._session.flush()
        elif workspace.owner_user_id != user.id:
            raise AuthRepositoryError(
                "seed workspace slug is already owned by another user"
            )
        else:
            workspace.name = display_name
            workspace.updated_at = now

        self._session.commit()
        self._session.refresh(user)
        self._session.refresh(workspace)
        return user, workspace

    def _now(self) -> datetime:
        return _aware_utc(self._clock())


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _require_workspace_slug(value: str) -> str:
    slug = value.strip()
    if not slug:
        raise AuthRepositoryError("seed workspace slug must not be empty")
    if "/" in slug:
        raise AuthRepositoryError("seed workspace slug must not contain slashes")
    return slug
