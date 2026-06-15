from __future__ import annotations

from quantitative_sentiment_analysis.backtest_dataset.repository import (
    CompletedDatasetRepository,
)
from quantitative_sentiment_analysis.backtest_dataset.schemas import DatasetRunStatus
from quantitative_sentiment_analysis.contracts import DatasetRecord
from quantitative_sentiment_analysis.contracts.serialization import (
    dataset_record_jsonl_line,
    stable_json_data,
)


class DatasetExportNotReadyError(RuntimeError):
    """Raised when a stored dataset run is not exportable as JSONL."""


def export_dataset_jsonl_bytes(
    repository: CompletedDatasetRepository,
    workspace_id: str,
    run_id: str,
) -> bytes:
    preview = repository.get_run(workspace_id, run_id)
    if preview.summary.status is not DatasetRunStatus.COMPLETED:
        raise DatasetExportNotReadyError(
            "BACKTEST dataset export requires a COMPLETED deterministic dataset "
            f"run; found status {preview.summary.status}"
        )

    records = repository.list_records(workspace_id, run_id)
    lines = (
        dataset_record_jsonl_line(record)
        for record in sorted(records, key=_dataset_export_sort_key)
    )
    return "".join(lines).encode("utf-8")


def _dataset_export_sort_key(record: DatasetRecord) -> tuple[str, str, str, str]:
    timestamp = stable_json_data(record.timestamp)
    if not isinstance(timestamp, str):
        raise TypeError("stable timestamp serialization must produce a string")
    source_identity = "\u0000".join((record.source_id or "", record.source_name or ""))
    return (
        timestamp,
        record.record_id or "",
        source_identity,
        record.headline,
    )
