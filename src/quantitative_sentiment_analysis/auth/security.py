from __future__ import annotations

import hmac
import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Response

AUTH_SECRET_ENV = "AUTH_SECRET"
QSA_SESSION_COOKIE_NAME = "QSA_SESSION_COOKIE_NAME"
QSA_SESSION_COOKIE_SECURE = "QSA_SESSION_COOKIE_SECURE"
QSA_SESSION_COOKIE_SAMESITE = "QSA_SESSION_COOKIE_SAMESITE"
QSA_SESSION_TTL_SECONDS = "QSA_SESSION_TTL_SECONDS"

DEFAULT_SESSION_COOKIE_NAME = "qsa_session"
DEFAULT_SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
MIN_AUTH_SECRET_LENGTH = 32

SameSite = Literal["lax", "strict", "none"]

_PASSWORD_HASHER = PasswordHasher(type=Type.ID)


class AuthConfigurationError(RuntimeError):
    """Raised when auth cannot run safely with the current environment."""


@dataclass(frozen=True)
class SessionCookieSettings:
    name: str
    secure: bool
    same_site: SameSite
    max_age_seconds: int
    path: str = "/"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def token_digest(
    token: str,
    *,
    secret: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    if not token:
        raise ValueError("session token must not be empty")
    auth_secret = secret if secret is not None else configured_auth_secret(env)
    return hmac.new(
        auth_secret.encode("utf-8"),
        token.encode("utf-8"),
        sha256,
    ).hexdigest()


def configured_auth_secret(env: Mapping[str, str] | None = None) -> str:
    source = env if env is not None else os.environ
    secret = source.get(AUTH_SECRET_ENV, "").strip()
    if len(secret) < MIN_AUTH_SECRET_LENGTH:
        raise AuthConfigurationError(
            f"{AUTH_SECRET_ENV} must be set to at least "
            f"{MIN_AUTH_SECRET_LENGTH} characters"
        )
    return secret


def session_cookie_settings(
    env: Mapping[str, str] | None = None,
) -> SessionCookieSettings:
    source = env if env is not None else os.environ
    name = source.get(QSA_SESSION_COOKIE_NAME, DEFAULT_SESSION_COOKIE_NAME).strip()
    if not name:
        raise AuthConfigurationError(f"{QSA_SESSION_COOKIE_NAME} must not be empty")

    secure = _read_bool(source.get(QSA_SESSION_COOKIE_SECURE), default=True)
    same_site = _read_same_site(source.get(QSA_SESSION_COOKIE_SAMESITE), secure=secure)
    ttl_seconds = _read_positive_int(
        source.get(QSA_SESSION_TTL_SECONDS),
        default=DEFAULT_SESSION_TTL_SECONDS,
        env_name=QSA_SESSION_TTL_SECONDS,
    )
    return SessionCookieSettings(
        name=name,
        secure=secure,
        same_site=same_site,
        max_age_seconds=ttl_seconds,
    )


def set_session_cookie(
    response: Response,
    token: str,
    *,
    settings: SessionCookieSettings | None = None,
) -> None:
    cookie_settings = settings or session_cookie_settings()
    response.set_cookie(
        key=cookie_settings.name,
        value=token,
        max_age=cookie_settings.max_age_seconds,
        path=cookie_settings.path,
        secure=cookie_settings.secure,
        httponly=True,
        samesite=cookie_settings.same_site,
    )


def clear_session_cookie(
    response: Response,
    *,
    settings: SessionCookieSettings | None = None,
) -> None:
    cookie_settings = settings or session_cookie_settings()
    response.set_cookie(
        key=cookie_settings.name,
        value="",
        max_age=0,
        expires=0,
        path=cookie_settings.path,
        secure=cookie_settings.secure,
        httponly=True,
        samesite=cookie_settings.same_site,
    )


def session_ttl_seconds(env: Mapping[str, str] | None = None) -> int:
    return session_cookie_settings(env).max_age_seconds


def _read_bool(value: str | None, *, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise AuthConfigurationError("boolean auth settings must use true or false")


def _read_same_site(value: str | None, *, secure: bool) -> SameSite:
    if value is None or not value.strip():
        return "none" if secure else "lax"
    normalized = value.strip().lower()
    if normalized not in {"lax", "strict", "none"}:
        raise AuthConfigurationError(
            f"{QSA_SESSION_COOKIE_SAMESITE} must be lax, strict, or none"
        )
    return normalized  # pyright: ignore[reportReturnType]


def _read_positive_int(value: str | None, *, default: int, env_name: str) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise AuthConfigurationError(f"{env_name} must be an integer") from exc
    if parsed <= 0:
        raise AuthConfigurationError(f"{env_name} must be greater than zero")
    return parsed
