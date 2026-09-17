"""Database tables.

Two things worth knowing before reading:

1. Generated apps do not get their own tables. Every record they hold lives in
   `records`, keyed by `project_id` and `entity_name`, with the values in a
   JSON column. That means no schema changes at run time, no migrations per
   customer, and no way for one app's shape to break another's.

2. There are two kinds of user. `User` is our customer, the person who builds
   apps. `AppUser` is one of *their* staff, who can only ever log into the one
   published app they belong to. They are separate tables on purpose.

Column types stay portable so the same models run on SQLite locally and
Postgres in production.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return uuid.uuid4().hex


def new_token() -> str:
    return secrets.token_urlsafe(32)


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(moment: datetime) -> datetime:
    """Make a stored timestamp safe to compare against `utcnow()`.

    SQLite has no timezone type, so a datetime read back from it is naive even
    though it was written as UTC. Subtracting that from an aware datetime
    raises, which is a crash in the middle of an approval — so every timestamp
    read from the database goes through here first.
    """
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


PrimaryKey = Mapped[str]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


# --------------------------------------------------------------------------
# Enums stored as short strings
# --------------------------------------------------------------------------


class ProjectKind(StrEnum):
    SITE = "site"
    APP = "app"


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class RunStatus(StrEnum):
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(StrEnum):
    OK = "ok"
    SKIPPED = "skipped"
    WAITING = "waiting"
    FAILED = "failed"


class ApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# --------------------------------------------------------------------------
# Platform side — our customers
# --------------------------------------------------------------------------


class User(Base, TimestampMixin):
    """A person who builds apps and sites on the platform."""

    __tablename__ = "users"

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    #: Set when the account came from an OAuth provider instead of a password.
    oauth_provider: Mapped[str | None] = mapped_column(String(32))
    oauth_subject: Mapped[str | None] = mapped_column(String(255), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    projects: Mapped[list[Project]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )


class Project(Base, TimestampMixin):
    """One built thing — either a published website or a workflow app."""

    __tablename__ = "projects"

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(48), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), default=ProjectStatus.DRAFT, nullable=False
    )

    #: The prompt this was built from, kept so the user can see and re-run it.
    source_prompt: Mapped[str | None] = mapped_column(Text)

    #: The spec being edited. `published_spec` is the frozen copy being served,
    #: so editing a draft never changes what visitors see until Publish.
    draft_spec: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    published_spec: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[User] = relationship(back_populates="projects")
    app_users: Mapped[list[AppUser]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def is_published(self) -> bool:
        return self.status == ProjectStatus.PUBLISHED and self.published_spec is not None

    @property
    def live_spec(self) -> dict[str, Any] | None:
        """What the runtime should serve: the published copy if there is one."""
        return self.published_spec or self.draft_spec


# --------------------------------------------------------------------------
# Generated-app side — our customers' staff
# --------------------------------------------------------------------------


class AppUser(Base, TimestampMixin):
    """Someone who logs into one published app. Scoped to that app only."""

    __tablename__ = "app_users"
    __table_args__ = (
        UniqueConstraint("project_id", "email", name="uq_app_user_email_per_project"),
    )

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    #: A role name from the app's spec, e.g. "manager".
    role: Mapped[str] = mapped_column(String(48), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    #: Set while an invite is outstanding; cleared once they set a password.
    invite_token: Mapped[str | None] = mapped_column(String(64), index=True)
    invite_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped[Project] = relationship(back_populates="app_users")

    @property
    def is_pending_invite(self) -> bool:
        return self.password_hash is None


class Record(Base, TimestampMixin):
    """One row of one entity of one app. The shared data table.

    Never query this directly — go through `app.runtime.records`, which will
    not let you forget the project scope.
    """

    __tablename__ = "records"
    __table_args__ = (
        Index("ix_records_project_entity", "project_id", "entity_name"),
        Index("ix_records_project_entity_created", "project_id", "entity_name", "created_at"),
    )

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_name: Mapped[str] = mapped_column(String(48), nullable=False)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    #: The app_user who created this. Null when a workflow created it.
    created_by: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("app_users.id", ondelete="SET NULL"), index=True
    )


# --------------------------------------------------------------------------
# Workflow execution
# --------------------------------------------------------------------------


class WorkflowRun(Base, TimestampMixin):
    """One execution of one workflow, and everything needed to resume it."""

    __tablename__ = "workflow_runs"
    __table_args__ = (Index("ix_runs_project_status", "project_id", "status"),)

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_key: Mapped[str] = mapped_column(String(48), nullable=False)
    #: Human-readable counter, per project. "Run #14" is what users refer to.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    status: Mapped[str] = mapped_column(String(24), default=RunStatus.RUNNING, nullable=False)

    #: The resolved run context — trigger data, step outputs, vars. This is
    #: what makes a run resumable days after it paused.
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    #: The step to execute next, or the one we are paused on.
    cursor: Mapped[str | None] = mapped_column(String(48))

    #: True for a dry run from the Test button: it never writes real records
    #: and never sends anything.
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    #: The spec this run started against, so an edit mid-run cannot change the
    #: rules a paused run finishes under.
    workflow_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    error: Mapped[str | None] = mapped_column(Text)
    failed_step: Mapped[str | None] = mapped_column(String(48))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    steps: Mapped[list[WorkflowRunStep]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="WorkflowRunStep.position",
    )


class WorkflowRunStep(Base):
    """One step of one run, logged so a failure can actually be diagnosed."""

    __tablename__ = "workflow_run_steps"
    __table_args__ = (Index("ix_run_steps_run", "run_id", "position"),)

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    step_id: Mapped[str] = mapped_column(String(48), nullable=False)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)

    #: What the step was given and what it produced, for the run log.
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    run: Mapped[WorkflowRun] = relationship(back_populates="steps")


class Approval(Base, TimestampMixin):
    """A decision a run is waiting on. Also what fills an approvals screen."""

    __tablename__ = "approvals"
    __table_args__ = (
        Index("ix_approvals_project_role_decision", "project_id", "role", "decision"),
    )

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(String(48), nullable=False)

    #: The role allowed to decide this.
    role: Mapped[str] = mapped_column(String(48), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(48), nullable=False)
    record_id: Mapped[str | None] = mapped_column(String(32), index=True)
    prompt: Mapped[str] = mapped_column(String(200), nullable=False)

    decision: Mapped[str] = mapped_column(
        String(16), default=ApprovalDecision.PENDING, nullable=False
    )
    decided_by: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("app_users.id", ondelete="SET NULL")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


class Notification(Base):
    """An in-app message for one app user."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_recipient", "app_user_id", "read_at"),)

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    app_user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="", nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(32))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class OutboundEmail(Base):
    """An email we intend to send.

    Written inside the same transaction as the step that asked for it, then
    delivered by a worker. A run is never held up by an email provider, and a
    crash mid-run cannot lose the intent to send.
    """

    __tablename__ = "outbound_emails"
    __table_args__ = (Index("ix_outbound_pending", "sent_at", "attempts"),)

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    project_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(32))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class UsageEvent(Base):
    """One billable or rate-limited thing happening.

    Recorded from day one even though nothing is charged yet, so that when
    pricing is switched on the real margin is already known.
    """

    __tablename__ = "usage_events"
    __table_args__ = (Index("ix_usage_user_kind_time", "user_id", "kind", "created_at"),)

    id: PrimaryKey = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(32), index=True)
    #: "generation", "workflow_run", "ai_classify"
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    #: Micro-rupees, to stay in integers.
    cost_micros: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
