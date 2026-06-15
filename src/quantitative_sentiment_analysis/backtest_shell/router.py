from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from quantitative_sentiment_analysis.backtest_shell.repository import (
    BacktestShellRepository,
    BacktestShellRunNotFoundError,
    BacktestShellUnsupportedError,
    get_backtest_shell_repository,
)
from quantitative_sentiment_analysis.backtest_shell.schemas import (
    BacktestRunShell,
    CreateBacktestRunRequest,
)

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}/backtests",
    tags=["backtest-shell"],
)


@router.post("/drafts", response_model=BacktestRunShell)
def create_draft_backtest_run(
    workspace_id: str,
    request: CreateBacktestRunRequest,
    repository: Annotated[
        BacktestShellRepository,
        Depends(get_backtest_shell_repository),
    ],
) -> BacktestRunShell:
    try:
        return repository.create_draft_run(workspace_id, request)
    except BacktestShellUnsupportedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{run_id}", response_model=BacktestRunShell)
def get_backtest_run_shell(
    workspace_id: str,
    run_id: str,
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
