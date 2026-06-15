from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder

from quantitative_sentiment_analysis.backtest_dataset.cryptopanic import (
    CryptoPanicClient,
)
from quantitative_sentiment_analysis.backtest_dataset.orchestrator import (
    DatasetOrchestrator,
)
from quantitative_sentiment_analysis.backtest_dataset.provider import (
    HistoricalNewsProvider,
)
from quantitative_sentiment_analysis.backtest_dataset.repository import (
    CompletedDatasetRepository,
    CompletedDatasetRunNotFoundError,
    get_completed_dataset_repository,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import (
    DatasetRunPreview,
    DatasetRunStatus,
)
from quantitative_sentiment_analysis.backtest_shell.repository import (
    BacktestShellRepository,
    BacktestShellRunNotFoundError,
    BacktestShellUnsupportedError,
    get_backtest_shell_repository,
)

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}/backtests",
    tags=["backtest-dataset"],
)


def get_historical_news_provider() -> HistoricalNewsProvider:
    return CryptoPanicClient()


def get_dataset_orchestrator(
    shell_repository: Annotated[
        BacktestShellRepository,
        Depends(get_backtest_shell_repository),
    ],
    completed_repository: Annotated[
        CompletedDatasetRepository,
        Depends(get_completed_dataset_repository),
    ],
    provider: Annotated[
        HistoricalNewsProvider,
        Depends(get_historical_news_provider),
    ],
) -> DatasetOrchestrator:
    return DatasetOrchestrator(
        shell_repository=shell_repository,
        completed_repository=completed_repository,
        provider=provider,
    )


@router.post("/{run_id}/dataset/run", response_model=DatasetRunPreview)
def run_backtest_dataset(
    workspace_id: str,
    run_id: str,
    orchestrator: Annotated[
        DatasetOrchestrator,
        Depends(get_dataset_orchestrator),
    ],
) -> DatasetRunPreview:
    try:
        preview = orchestrator.run_dataset(workspace_id=workspace_id, run_id=run_id)
    except BacktestShellRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BacktestShellUnsupportedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if preview.summary.status is DatasetRunStatus.FAILED_PROVIDER_LIMITATION:
        raise HTTPException(status_code=409, detail=jsonable_encoder(preview))
    return preview


@router.get("/{run_id}/dataset", response_model=DatasetRunPreview)
def get_backtest_dataset(
    workspace_id: str,
    run_id: str,
    repository: Annotated[
        CompletedDatasetRepository,
        Depends(get_completed_dataset_repository),
    ],
) -> DatasetRunPreview:
    try:
        return repository.get_run(workspace_id, run_id)
    except CompletedDatasetRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
