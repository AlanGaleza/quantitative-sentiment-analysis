from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder

from quantitative_sentiment_analysis.backtest_dataset.export import (
    DatasetExportNotReadyError,
    export_dataset_jsonl_bytes,
)
from quantitative_sentiment_analysis.backtest_dataset.sharpe import (
    SharpeTerminalClient,
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
    return SharpeTerminalClient()


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


@router.get("/{run_id}/dataset/export.jsonl")
def export_backtest_dataset_jsonl(
    workspace_id: str,
    run_id: str,
    repository: Annotated[
        CompletedDatasetRepository,
        Depends(get_completed_dataset_repository),
    ],
) -> Response:
    try:
        preview = repository.get_run(workspace_id, run_id)
        body = export_dataset_jsonl_bytes(repository, workspace_id, run_id)
    except CompletedDatasetRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DatasetExportNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    filename = (
        f"{_safe_filename_part(workspace_id)}-"
        f"{_safe_filename_part(run_id)}-dataset.jsonl"
    )
    return Response(
        content=body,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-QSA-Workspace-Id": preview.summary.workspace_id,
            "X-QSA-Run-Id": preview.summary.run_id,
            "X-QSA-Config-Version": preview.summary.config_version,
            "X-QSA-Model-Version": preview.summary.model_version,
        },
    )


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


def _safe_filename_part(value: str) -> str:
    sanitized = "".join(
        character
        if character.isascii()
        and (character.isalnum() or character in {"-", "_", "."})
        else "_"
        for character in value
    )
    return sanitized or "dataset"
