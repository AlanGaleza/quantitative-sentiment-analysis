from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative metadata for Alembic and durable persistence repositories."""


class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sessions: Mapped[list[SessionModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    workspaces: Mapped[list[WorkspaceModel]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class SessionModel(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
        Index("ix_sessions_user_expires_at", "user_id", "expires_at"),
        Index("ix_sessions_token_hash", "token_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[UserModel] = relationship(back_populates="sessions")


class WorkspaceModel(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_workspaces_slug"),
        Index("ix_workspaces_owner_user_id", "owner_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    owner: Mapped[UserModel] = relationship(back_populates="workspaces")
    configs: Mapped[list[BacktestConfigModel]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list[BacktestRunModel]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )


class BacktestConfigModel(Base):
    __tablename__ = "backtest_configs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            name="uq_backtest_configs_workspace_name",
        ),
        CheckConstraint("instrument = 'BTCUSD'", name="ck_backtest_configs_btcusd"),
        CheckConstraint("mode = 'BACKTEST'", name="ck_backtest_configs_backtest"),
        CheckConstraint(
            "timeframe_end >= timeframe_start",
            name="ck_backtest_configs_timeframe_order",
        ),
        Index("ix_backtest_configs_workspace_id", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    instrument: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    timeframe_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="configs")
    runs: Mapped[list[BacktestRunModel]] = relationship(back_populates="config")


class BacktestRunModel(Base):
    __tablename__ = "backtest_runs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "run_id",
            name="uq_backtest_runs_workspace_run_id",
        ),
        CheckConstraint("instrument = 'BTCUSD'", name="ck_backtest_runs_btcusd"),
        CheckConstraint("mode = 'BACKTEST'", name="ck_backtest_runs_backtest"),
        CheckConstraint(
            "status IN ('DRAFT', 'READY_FOR_DATASET')",
            name="ck_backtest_runs_status",
        ),
        CheckConstraint(
            "timeframe_end >= timeframe_start",
            name="ck_backtest_runs_timeframe_order",
        ),
        Index("ix_backtest_runs_workspace_run_id", "workspace_id", "run_id"),
        Index(
            "ix_backtest_runs_workspace_created_run",
            "workspace_id",
            "created_at",
            "run_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    config_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("backtest_configs.id", ondelete="SET NULL"),
    )
    instrument: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    timeframe_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    workspace: Mapped[WorkspaceModel] = relationship(back_populates="runs")
    config: Mapped[BacktestConfigModel | None] = relationship(back_populates="runs")
    dataset_run: Mapped[DatasetRunModel | None] = relationship(
        back_populates="backtest_run",
        cascade="all, delete-orphan",
        uselist=False,
    )


class DatasetRunModel(Base):
    __tablename__ = "dataset_runs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "run_id",
            name="uq_dataset_runs_workspace_run_id",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "run_id"],
            ["backtest_runs.workspace_id", "backtest_runs.run_id"],
            ondelete="CASCADE",
            name="fk_dataset_runs_backtest_run",
        ),
        CheckConstraint("instrument = 'BTCUSD'", name="ck_dataset_runs_btcusd"),
        CheckConstraint("mode = 'BACKTEST'", name="ck_dataset_runs_backtest"),
        CheckConstraint(
            "status IN ('COMPLETED', 'FAILED_PROVIDER_LIMITATION')",
            name="ck_dataset_runs_terminal_status",
        ),
        CheckConstraint(
            "record_count = relevant_count + noise_count + irrelevant_count",
            name="ck_dataset_runs_relevance_total",
        ),
        CheckConstraint("record_count >= 0", name="ck_dataset_runs_record_count_nonnegative"),
        CheckConstraint(
            "relevant_count >= 0",
            name="ck_dataset_runs_relevant_count_nonnegative",
        ),
        CheckConstraint("noise_count >= 0", name="ck_dataset_runs_noise_count_nonnegative"),
        CheckConstraint(
            "irrelevant_count >= 0",
            name="ck_dataset_runs_irrelevant_count_nonnegative",
        ),
        CheckConstraint(
            "status != 'FAILED_PROVIDER_LIMITATION' "
            "OR provider_limitation_reason IS NOT NULL",
            name="ck_dataset_runs_limitation_reason_required",
        ),
        CheckConstraint(
            "status != 'COMPLETED' OR provider_limitation_reason IS NULL",
            name="ck_dataset_runs_completed_without_limitation",
        ),
        Index("ix_dataset_runs_workspace_run_id", "workspace_id", "run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    instrument: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    timeframe_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    timeframe_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    record_count: Mapped[int] = mapped_column(nullable=False)
    relevant_count: Mapped[int] = mapped_column(nullable=False)
    noise_count: Mapped[int] = mapped_column(nullable=False)
    irrelevant_count: Mapped[int] = mapped_column(nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    config_version: Mapped[str] = mapped_column(String(128), nullable=False)
    input_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_limitation_provider_name: Mapped[str | None] = mapped_column(String(255))
    provider_limitation_reason: Mapped[str | None] = mapped_column(String(255))
    provider_limitation_detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    backtest_run: Mapped[BacktestRunModel] = relationship(back_populates="dataset_run")
    records: Mapped[list[DatasetRecordModel]] = relationship(
        back_populates="dataset_run",
        cascade="all, delete-orphan",
    )


class DatasetRecordModel(Base):
    __tablename__ = "dataset_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "run_id"],
            ["dataset_runs.workspace_id", "dataset_runs.run_id"],
            ondelete="CASCADE",
            name="fk_dataset_records_dataset_run",
        ),
        CheckConstraint("instrument = 'BTCUSD'", name="ck_dataset_records_btcusd"),
        CheckConstraint("mode = 'BACKTEST'", name="ck_dataset_records_backtest"),
        CheckConstraint(
            "directional_bias IN ('LONG', 'SHORT', 'FLAT')",
            name="ck_dataset_records_directional_bias",
        ),
        CheckConstraint(
            "relevance IN ('RELEVANT', 'NOISE', 'IRRELEVANT')",
            name="ck_dataset_records_relevance",
        ),
        CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="ck_dataset_records_sentiment_score_bounds",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_dataset_records_confidence_bounds",
        ),
        CheckConstraint(
            "source_id IS NOT NULL OR source_name IS NOT NULL",
            name="ck_dataset_records_source_identity",
        ),
        Index("ix_dataset_records_workspace_run_id", "workspace_id", "run_id"),
        Index("ix_dataset_records_export_order", "workspace_id", "run_id", "timestamp"),
        UniqueConstraint(
            "workspace_id",
            "run_id",
            "record_id",
            name="uq_dataset_records_workspace_run_record_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    run_id: Mapped[str] = mapped_column(String(128), nullable=False)
    record_id: Mapped[str | None] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255))
    source_name: Mapped[str | None] = mapped_column(String(255))
    instrument: Mapped[str] = mapped_column(String(16), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)
    directional_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    relevance: Mapped[str] = mapped_column(String(16), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    config_version: Mapped[str] = mapped_column(String(128), nullable=False)

    dataset_run: Mapped[DatasetRunModel] = relationship(back_populates="records")
