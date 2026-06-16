from __future__ import annotations

import pytest
from fastapi import Response

from quantitative_sentiment_analysis.auth.security import (
    AUTH_SECRET_ENV,
    QSA_SESSION_COOKIE_SECURE,
    AuthConfigurationError,
    clear_session_cookie,
    generate_session_token,
    hash_password,
    session_cookie_settings,
    set_session_cookie,
    token_digest,
    verify_password,
)

AUTH_SECRET = "x" * 48


def test_password_hashing_uses_argon2id_and_verifies_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2id$")
    assert "correct horse" not in password_hash
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_session_tokens_are_opaque_and_hmac_digests_are_stable() -> None:
    first = generate_session_token()
    second = generate_session_token()

    assert first != second
    assert len(first) >= 48
    assert token_digest(first, secret=AUTH_SECRET) == token_digest(
        first,
        secret=AUTH_SECRET,
    )
    assert token_digest(first, secret=AUTH_SECRET) != token_digest(
        second,
        secret=AUTH_SECRET,
    )
    assert len(token_digest(first, secret=AUTH_SECRET)) == 64


def test_token_digest_requires_configured_auth_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(AUTH_SECRET_ENV, raising=False)

    with pytest.raises(AuthConfigurationError, match=AUTH_SECRET_ENV):
        token_digest("session-token")


def test_default_cookie_settings_are_production_cross_site_safe() -> None:
    settings = session_cookie_settings(env={})

    assert settings.name == "qsa_session"
    assert settings.secure is True
    assert settings.same_site == "none"
    assert settings.max_age_seconds > 0


def test_local_cookie_settings_can_explicitly_disable_secure_cookie() -> None:
    settings = session_cookie_settings(env={QSA_SESSION_COOKIE_SECURE: "false"})

    assert settings.secure is False
    assert settings.same_site == "lax"


def test_cookie_helpers_set_and_clear_httponly_session_cookie() -> None:
    response = Response()
    set_session_cookie(
        response,
        "raw-token",
        settings=session_cookie_settings(env={}),
    )

    header = response.headers["set-cookie"]
    assert "qsa_session=raw-token" in header
    assert "HttpOnly" in header
    assert "Secure" in header
    assert "SameSite=none" in header

    clear_response = Response()
    clear_session_cookie(
        clear_response,
        settings=session_cookie_settings(env={}),
    )

    clear_header = clear_response.headers["set-cookie"]
    assert "qsa_session=" in clear_header
    assert "Max-Age=0" in clear_header
