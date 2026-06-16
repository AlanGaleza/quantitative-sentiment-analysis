from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from quantitative_sentiment_analysis.auth.dependencies import (
    get_auth_repository,
    require_current_user,
)
from quantitative_sentiment_analysis.auth.repository import AuthRepository
from quantitative_sentiment_analysis.auth.schemas import (
    AuthSessionResponse,
    CurrentUser,
    CurrentWorkspace,
    LoginRequest,
)
from quantitative_sentiment_analysis.auth.security import (
    clear_session_cookie,
    session_cookie_settings,
    set_session_cookie,
)
from quantitative_sentiment_analysis.persistence.models import UserModel, WorkspaceModel

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthSessionResponse)
def login(
    request: LoginRequest,
    response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> AuthSessionResponse:
    user = repository.authenticate_user(request.email, request.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
        )
    token = repository.create_session(user)
    set_session_cookie(response, token)
    return _auth_session_response(repository, user)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> dict[str, str]:
    token = request.cookies.get(session_cookie_settings().name)
    if token:
        repository.revoke_session(token)
    clear_session_cookie(response)
    return {"status": "ok"}


@router.get("/me", response_model=AuthSessionResponse)
def me(
    current_user: Annotated[UserModel, Depends(require_current_user)],
    repository: Annotated[AuthRepository, Depends(get_auth_repository)],
) -> AuthSessionResponse:
    return _auth_session_response(repository, current_user)


def _auth_session_response(
    repository: AuthRepository,
    user: UserModel,
) -> AuthSessionResponse:
    workspaces = repository.load_owned_workspaces(user.id)
    workspace_responses = tuple(
        _current_workspace_response(workspace) for workspace in workspaces
    )
    return AuthSessionResponse(
        user=CurrentUser(id=str(user.id), email=user.email),
        workspaces=workspace_responses,
        default_workspace_slug=(
            workspace_responses[0].slug if workspace_responses else None
        ),
    )


def _current_workspace_response(workspace: WorkspaceModel) -> CurrentWorkspace:
    return CurrentWorkspace(
        id=str(workspace.id),
        slug=workspace.slug,
        name=workspace.name,
    )
