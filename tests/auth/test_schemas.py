from __future__ import annotations

import pytest
from pydantic import ValidationError

from quantitative_sentiment_analysis.auth.schemas import (
    AuthSessionResponse,
    CurrentUser,
    CurrentWorkspace,
    LoginRequest,
)


def test_login_request_normalizes_email_without_trimming_password() -> None:
    request = LoginRequest(email=" Trader@Example.TEST ", password="  secret  ")

    assert request.email == "trader@example.test"
    assert request.password == "  secret  "


def test_login_request_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(email="trader@example.test", password="secret", token="raw")


def test_auth_session_response_exposes_user_and_workspace_without_token() -> None:
    response = AuthSessionResponse(
        user=CurrentUser(id="user-1", email="trader@example.test"),
        workspaces=(
            CurrentWorkspace(
                id="workspace-1",
                slug="demo-workspace",
                name="Demo Workspace",
            ),
        ),
        default_workspace_slug="demo-workspace",
    )

    payload = response.model_dump()
    assert payload["user"]["email"] == "trader@example.test"
    assert payload["workspaces"][0]["slug"] == "demo-workspace"
    assert "password" not in str(payload).lower()
    assert "token" not in str(payload).lower()
