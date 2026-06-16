from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from quantitative_sentiment_analysis.auth.dependencies import require_owned_workspace
from quantitative_sentiment_analysis.backtest_shell.repository import (
    BacktestShellRepository,
    BacktestShellRunNotFoundError,
    BacktestShellUnsupportedError,
    get_backtest_shell_repository,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import (
    BacktestRunHistoryResponse,
    BacktestRunShell,
    CreateBacktestRunRequest,
    DEFAULT_BACKTEST_RUN_HISTORY_LIMIT,
    MAX_BACKTEST_RUN_HISTORY_LIMIT,
)
from quantitative_sentiment_analysis.persistence.models import WorkspaceModel

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}/backtests",
    tags=["backtest-shell"],
)


@router.post("/drafts", response_model=BacktestRunShell)
def create_draft_backtest_run(
    workspace_id: str,
    request: CreateBacktestRunRequest,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestShellRepository,
        Depends(get_backtest_shell_repository),
    ],
) -> BacktestRunShell:
    try:
        return repository.create_draft_run(workspace_id, request)
    except BacktestShellUnsupportedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=BacktestRunHistoryResponse)
def list_backtest_runs(
    workspace_id: str,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestShellRepository,
        Depends(get_backtest_shell_repository),
    ],
    limit: int = Query(
        default=DEFAULT_BACKTEST_RUN_HISTORY_LIMIT,
        ge=1,
        le=MAX_BACKTEST_RUN_HISTORY_LIMIT,
    ),
) -> BacktestRunHistoryResponse:
    try:
        return repository.list_runs(workspace_id, limit=limit)
    except BacktestShellRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BacktestShellUnsupportedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{run_id}", response_model=BacktestRunShell)
def get_backtest_run_shell(
    workspace_id: str,
    run_id: str,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    repository: Annotated[
        BacktestShellRepository,
        Depends(get_backtest_shell_repository),
    ],
) -> BacktestRunShell:
    try:
        return repository.get_run(workspace_id, run_id)
    except BacktestShellRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BacktestShellUnsupportedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
