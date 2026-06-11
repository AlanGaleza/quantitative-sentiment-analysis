from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
import json
from typing import Any

from pydantic import BaseModel

from quantitative_sentiment_analysis.contracts.schemas import (
    BacktestRunMetadata,
    DatasetRecord,
)


def stable_json_data(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return stable_json_data(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        return _stable_datetime(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): stable_json_data(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [stable_json_data(item) for item in value]
    return value


def stable_json_dumps(value: Any) -> str:
    return json.dumps(
        stable_json_data(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def dataset_record_jsonl_line(record: DatasetRecord) -> str:
    return f"{stable_json_dumps(record)}\n"


def run_fingerprint_material(metadata: BacktestRunMetadata) -> dict[str, Any]:
    data = stable_json_data(metadata)
    data.pop("run_id", None)
    return data


def stable_run_fingerprint(metadata: BacktestRunMetadata) -> str:
    payload = stable_json_dumps(run_fingerprint_material(metadata)).encode("utf-8")
    return sha256(payload).hexdigest()


def _stable_datetime(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include timezone information")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
