from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from quantitative_sentiment_analysis.auth.repository import AuthRepository
from quantitative_sentiment_analysis.auth.security import session_cookie_settings
from quantitative_sentiment_analysis.persistence.database import get_database_session
from quantitative_sentiment_analysis.persistence.models import UserModel, WorkspaceModel


def get_auth_repository(
    session: Annotated[Session, Depends(get_database_session)],
) -> AuthRepository:
    return AuthRepository(session)


def require_current_user(
    request: Request,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> UserModel:
    token = request.cookies.get(session_cookie_settings().name)
    if token is None:
        raise_not_authenticated()
    user = repository.resolve_current_user(token)
    if user is None:
        raise_not_authenticated()
    return user


def require_owned_workspace(
    workspace_id: str,
    current_user: Annotated[UserModel, Depends(require_current_user)],
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> WorkspaceModel:
    workspace = repository.get_owned_workspace(
        user_id=current_user.id,
        workspace_slug=workspace_id,
    )
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return workspace


def raise_not_authenticated() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="not authenticated",
    )
