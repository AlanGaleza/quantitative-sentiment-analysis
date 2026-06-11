from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from quantitative_sentiment_analysis.backtest_quality.schemas import QualityInputRecord


class QualityRunNotReadyError(RuntimeError):
    """Raised when real S-02 completed-run storage is not available yet."""


class QualityRunNotFoundError(RuntimeError):
    """Raised when a workspace/run pair does not exist."""


class QualityRunIncompleteError(RuntimeError):
    """Raised when a run exists but cannot be evaluated yet."""


class QualityRunUnsupportedError(RuntimeError):
    """Raised when a run is outside BTCUSD BACKTEST quality-view scope."""


class QualityInputProvider(Protocol):
    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
    ) -> Sequence[QualityInputRecord]:
        """Return deterministic quality inputs for one completed BACKTEST run."""


class NotReadyQualityInputProvider:
    def get_quality_inputs(
        self,
        workspace_id: str,
        run_id: str,
    ) -> Sequence[QualityInputRecord]:
        raise QualityRunNotReadyError(
            "S-02 deterministic completed-run storage is not integrated yet"
        )


def get_quality_input_provider() -> QualityInputProvider:
    return NotReadyQualityInputProvider()
