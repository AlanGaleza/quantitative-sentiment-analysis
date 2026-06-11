from __future__ import annotations

from fastapi.testclient import TestClient

from quantitative_sentiment_analysis.main import (
    QSA_CORS_ALLOWED_ORIGINS,
    configured_cors_allowed_origins,
    create_app,
)


def test_health_endpoint_keeps_smoke_contract() -> None:
    client = TestClient(create_app(cors_allowed_origins=[]))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "quantitative-sentiment-analysis"


def test_cors_allows_configured_frontend_origin() -> None:
    client = TestClient(
        create_app(cors_allowed_origins=["https://frontend.example.test"])
    )

    response = client.options(
        "/api/workspaces/workspace-alpha/backtests/run-001/quality",
        headers={
            "Origin": "https://frontend.example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"]
        == "https://frontend.example.test"
    )


def test_cors_rejects_unconfigured_frontend_origin() -> None:
    client = TestClient(
        create_app(cors_allowed_origins=["https://frontend.example.test"])
    )

    response = client.options(
        "/api/workspaces/workspace-alpha/backtests/run-001/quality",
        headers={
            "Origin": "https://other.example.test",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_cors_env_rejects_wildcard_origin(monkeypatch) -> None:
    monkeypatch.setenv(QSA_CORS_ALLOWED_ORIGINS, "*")

    try:
        configured_cors_allowed_origins()
    except ValueError as exc:
        assert "wildcard" in str(exc)
    else:
        raise AssertionError("wildcard CORS origin should be rejected")


def test_cors_env_rejects_non_http_origin(monkeypatch) -> None:
    monkeypatch.setenv(QSA_CORS_ALLOWED_ORIGINS, "file:///tmp/index.html")

    try:
        configured_cors_allowed_origins()
    except ValueError as exc:
        assert "http" in str(exc)
    else:
        raise AssertionError("non-http CORS origin should be rejected")


def test_cors_env_normalizes_trailing_slashes(monkeypatch) -> None:
    monkeypatch.setenv(
        QSA_CORS_ALLOWED_ORIGINS,
        "https://frontend.example.test/, http://localhost:5173/",
    )

    assert configured_cors_allowed_origins() == [
        "https://frontend.example.test",
        "http://localhost:5173",
    ]
