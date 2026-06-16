"""Closed-registration authentication and workspace ownership helpers."""

from quantitative_sentiment_analysis.auth.dependencies import (
    get_auth_repository,
    require_current_user,
    require_owned_workspace,
)
from quantitative_sentiment_analysis.auth.repository import (
    AuthRepository,
    AuthRepositoryError,
)
from quantitative_sentiment_analysis.auth.schemas import (
    AuthSessionResponse,
    CurrentUser,
    CurrentWorkspace,
    LoginRequest,
)
from quantitative_sentiment_analysis.auth.security import (
    AUTH_SECRET_ENV,
    QSA_SESSION_COOKIE_NAME,
    QSA_SESSION_COOKIE_SAMESITE,
    QSA_SESSION_COOKIE_SECURE,
    QSA_SESSION_TTL_SECONDS,
    AuthConfigurationError,
    clear_session_cookie,
    generate_session_token,
    hash_password,
    normalize_email,
    session_cookie_settings,
    set_session_cookie,
    token_digest,
    verify_password,
)

__all__ = [
    "AUTH_SECRET_ENV",
    "QSA_SESSION_COOKIE_NAME",
    "QSA_SESSION_COOKIE_SAMESITE",
    "QSA_SESSION_COOKIE_SECURE",
    "QSA_SESSION_TTL_SECONDS",
    "AuthConfigurationError",
    "AuthRepository",
    "AuthRepositoryError",
    "AuthSessionResponse",
    "CurrentUser",
    "CurrentWorkspace",
    "LoginRequest",
    "clear_session_cookie",
    "generate_session_token",
    "get_auth_repository",
    "hash_password",
    "normalize_email",
    "require_current_user",
    "require_owned_workspace",
    "session_cookie_settings",
    "set_session_cookie",
    "token_digest",
    "verify_password",
]
