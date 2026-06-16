from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from quantitative_sentiment_analysis.auth.dependencies import require_owned_workspace
from quantitative_sentiment_analysis.backtest_configs.repository import (
    BacktestConfigConflictError,
    BacktestConfigNotFoundError,
    BacktestConfigRepository,
    get_backtest_config_repository,
)
from quantitative_sentiment_analysis.backtest_configs.schemas import (
    BacktestConfigDetail,
    BacktestConfigListItem,
    CreateBacktestConfigRequest,
    CreateDraftFromConfigRequest,
    UpdateBacktestConfigRequest,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import BacktestRunShell
from quantitative_sentiment_analysis.persistence.models import WorkspaceModel

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}/backtest-configs",
    tags=["backtest-configs"],
)


@router.post("", response_model=BacktestConfigDetail)
def create_backtest_config(
    workspace_id: str,
    request: CreateBacktestConfigRequest,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestConfigRepository,
        Depends(get_backtest_config_repository),
    ],
) -> BacktestConfigDetail:
    try:
        return repository.create(workspace_id, request)
    except BacktestConfigConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=tuple[BacktestConfigListItem, ...])
def list_backtest_configs(
    workspace_id: str,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestConfigRepository,
        Depends(get_backtest_config_repository),
    ],
) -> tuple[BacktestConfigListItem, ...]:
    return repository.list(workspace_id)


@router.get("/{config_id}", response_model=BacktestConfigDetail)
def get_backtest_config(
    workspace_id: str,
    config_id: str,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestConfigRepository,
        Depends(get_backtest_config_repository),
    ],
) -> BacktestConfigDetail:
    try:
        return repository.get(workspace_id, config_id)
    except BacktestConfigNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{config_id}", response_model=BacktestConfigDetail)
def update_backtest_config(
    workspace_id: str,
    config_id: str,
    request: UpdateBacktestConfigRequest,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestConfigRepository,
        Depends(get_backtest_config_repository),
    ],
) -> BacktestConfigDetail:
    try:
        return repository.update(workspace_id, config_id, request)
    except BacktestConfigNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BacktestConfigConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/{config_id}", status_code=204)
def delete_backtest_config(
    workspace_id: str,
    config_id: str,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestConfigRepository,
        Depends(get_backtest_config_repository),
    ],
) -> Response:
    try:
        repository.delete(workspace_id, config_id)
    except BacktestConfigNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post("/{config_id}/drafts", response_model=BacktestRunShell)
def create_draft_from_backtest_config(
    workspace_id: str,
    config_id: str,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestConfigRepository,
        Depends(get_backtest_config_repository),
    ],
    request: CreateDraftFromConfigRequest | None = None,
) -> BacktestRunShell:
    try:
        return repository.create_draft_from_config(workspace_id, config_id)
    except BacktestConfigNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
