from __future__ import annotations

import os

from quantitative_sentiment_analysis.auth.repository import (
    AuthRepository,
    AuthRepositoryError,
)
from quantitative_sentiment_analysis.persistence.database import get_session_factory

QSA_SEED_USER_EMAIL = "QSA_SEED_USER_EMAIL"
QSA_SEED_USER_PASSWORD = "QSA_SEED_USER_PASSWORD"
QSA_SEED_WORKSPACE_SLUG = "QSA_SEED_WORKSPACE_SLUG"
QSA_SEED_WORKSPACE_NAME = "QSA_SEED_WORKSPACE_NAME"

DEFAULT_SEED_WORKSPACE_NAME = "Demo Workspace"


class SeedUserConfigurationError(RuntimeError):
    """Raised when the env-only seed command is missing required values."""


def main() -> None:
    email = _required_env(QSA_SEED_USER_EMAIL)
    password = _required_env(QSA_SEED_USER_PASSWORD)
    workspace_slug = _required_env(QSA_SEED_WORKSPACE_SLUG)
    workspace_name = os.getenv(QSA_SEED_WORKSPACE_NAME, DEFAULT_SEED_WORKSPACE_NAME)

    session_factory = get_session_factory()
    with session_factory() as session:
        try:
            user, workspace = AuthRepository(session).upsert_seed_user(
                email=email,
                password=password,
                workspace_slug=workspace_slug,
                workspace_name=workspace_name,
            )
        except AuthRepositoryError:
            session.rollback()
            raise

    print(
        "Seed user configured: "
        f"email={user.email} workspace={workspace.slug}"
    )


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SeedUserConfigurationError(f"{name} is required")
    return value


if __name__ == "__main__":
    main()
