from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

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
)

router = APIRouter(
    prefix="/api/workspaces/{workspace_id}/backtests",
    tags=["backtest-quality"],
)


@router.get("/{run_id}/quality", response_model=BacktestQualityReport)
def get_backtest_quality_report(
    workspace_id: str,
    run_id: str,
    provider: Annotated[QualityInputProvider, Depends(get_quality_input_provider)],
) -> BacktestQualityReport:
    try:
        records = provider.get_quality_inputs(workspace_id, run_id)
        report = build_quality_report(records)
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
