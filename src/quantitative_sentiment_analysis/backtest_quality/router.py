from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from quantitative_sentiment_analysis.auth.dependencies import require_owned_workspace
from quantitative_sentiment_analysis.backtest_quality.metrics import (
    QualityReportInputError,
    build_quality_report,
)
from quantitative_sentiment_analysis.backtest_quality.repository import (
    QualityInputProvider,
    QualityRunIncompleteError,
    QualityRunNotFoundError,
    QualityRunNotReadyError,
    QualityRunUnsupportedError,
    get_quality_input_provider,
)
from quantitative_sentiment_analysis.backtest_quality.schemas import (
    BacktestQualityReport,
    HorizonUnit,
    UnsupportedQualityHorizonError,
    supported_quality_horizon,
)
from quantitative_sentiment_analysis.persistence.models import WorkspaceModel

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}/backtests",
    tags=["backtest-quality"],
)


@router.get("/{run_id}/quality", response_model=BacktestQualityReport)
def get_backtest_quality_report(
    workspace_id: str,
    run_id: str,
    owned_workspace: Annotated[WorkspaceModel, Depends(require_owned_workspace)],
    provider: Annotated[QualityInputProvider, Depends(get_quality_input_provider)],
    horizon_value: int = Query(default=4, gt=0),
    horizon_unit: HorizonUnit = Query(default=HorizonUnit.HOURS),
) -> BacktestQualityReport:
    try:
        horizon = supported_quality_horizon(horizon_value, horizon_unit)
        batch = provider.get_quality_inputs(workspace_id, run_id, horizon)
        report = build_quality_report(
            batch.records,
            horizon=horizon,
            extra_warnings=batch.extra_warnings,
        )
    except UnsupportedQualityHorizonError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QualityRunNotReadyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QualityRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (QualityRunIncompleteError, QualityRunUnsupportedError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except QualityReportInputError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if report.workspace_id != workspace_id or report.run_id != run_id:
        raise HTTPException(
            status_code=409,
            detail="quality input provider returned records for a different workspace/run",
        )
    return report
