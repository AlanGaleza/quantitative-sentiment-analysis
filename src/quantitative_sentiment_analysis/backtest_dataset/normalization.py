from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quantitative_sentiment_analysis.contracts.schemas import require_aware_datetime


class ProviderNormalizationError(ValueError):
    """Raised when provider records cannot be normalized deterministically."""


class NormalizedNewsRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    provider_name: str = Field(min_length=1)
    provider_record_id: str | None = None
    timestamp: datetime
    headline: str = Field(min_length=1)
    body: str | None = None
    source_id: str | None = None
    source_name: str | None = None
    original_index: int = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @field_validator(
        "provider_record_id",
        "body",
        "source_id",
        "source_name",
        mode="before",
    )
    @classmethod
    def blank_strings_become_none(cls, value: object) -> object:
        if isinstance(value, str):
            value = _clean_text(value)
            return value or None
        return value

    @field_validator("headline", mode="before")
    @classmethod
    def headline_is_clean(cls, value: object) -> object:
        if isinstance(value, str):
            return _clean_text(value)
        return value


def normalize_provider_records(
    *,
    provider_name: str,
    raw_records: Iterable[Mapping[str, object]],
) -> tuple[NormalizedNewsRecord, ...]:
    normalized = tuple(
        _normalize_one(
            provider_name=provider_name,
            raw_record=raw_record,
            original_index=index,
        )
        for index, raw_record in enumerate(raw_records)
    )
    sorted_records = sorted(normalized, key=_sort_key)
    return _dedupe_exact_provider_ids(sorted_records)


def _normalize_one(
    *,
    provider_name: str,
    raw_record: Mapping[str, object],
    original_index: int,
) -> NormalizedNewsRecord:
    source = _mapping_value(raw_record.get("source"))
    return NormalizedNewsRecord(
        provider_name=provider_name,
        provider_record_id=_optional_text(
            raw_record.get("id")
            or raw_record.get("provider_record_id")
            or raw_record.get("record_id")
        ),
        timestamp=_timestamp_value(
            raw_record.get("published_at")
            or raw_record.get("timestamp")
            or raw_record.get("created_at")
        ),
        headline=_required_text(raw_record.get("title") or raw_record.get("headline")),
        body=_optional_text(raw_record.get("body") or raw_record.get("text") or raw_record.get("summary")),
        source_id=_optional_text(raw_record.get("source_id") or source.get("id")),
        source_name=_optional_text(raw_record.get("source_name") or source.get("title") or source.get("name")),
        original_index=original_index,
    )


def _dedupe_exact_provider_ids(
    records: list[NormalizedNewsRecord],
) -> tuple[NormalizedNewsRecord, ...]:
    seen_provider_ids: set[str] = set()
    deduped: list[NormalizedNewsRecord] = []
    for record in records:
        if record.provider_record_id is not None:
            if record.provider_record_id in seen_provider_ids:
                continue
            seen_provider_ids.add(record.provider_record_id)
        deduped.append(record)
    return tuple(deduped)


def _sort_key(record: NormalizedNewsRecord) -> tuple[str, str, str, str, str, int]:
    return (
        record.timestamp.isoformat(),
        record.provider_record_id or "",
        record.source_id or "",
        record.source_name or "",
        record.headline.casefold(),
        record.original_index,
    )


def _timestamp_value(value: object) -> datetime:
    if isinstance(value, datetime):
        try:
            return require_aware_datetime(value)
        except ValueError as exc:
            raise ProviderNormalizationError(
                "provider timestamp must include timezone information"
            ) from exc
    if isinstance(value, str):
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            return require_aware_datetime(datetime.fromisoformat(normalized))
        except ValueError as exc:
            raise ProviderNormalizationError(
                "provider timestamp is not valid ISO-8601 or is missing timezone information"
            ) from exc
    raise ProviderNormalizationError("provider timestamp is required")


def _required_text(value: object) -> str:
    text = _optional_text(value)
    if text is None:
        raise ProviderNormalizationError("provider headline is required")
    return text


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        value = str(value)
    if not isinstance(value, str):
        return None
    text = _clean_text(value)
    return text or None


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _mapping_value(value: object) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}
