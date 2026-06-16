from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quantitative_sentiment_analysis.auth.security import normalize_email


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("email")
    @classmethod
    def email_must_be_normalized(cls, value: str) -> str:
        normalized = normalize_email(value)
        if "@" not in normalized:
            raise ValueError("email must be a valid email address")
        return normalized


class CurrentUser(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    email: str = Field(min_length=3, max_length=320)


class CurrentWorkspace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    slug: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)


class AuthSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user: CurrentUser
    workspaces: tuple[CurrentWorkspace, ...]
    default_workspace_slug: str | None = Field(default=None, min_length=1)
