"""The published app, as its users see it.

These are the only routes a customer's staff ever touch. Every one of them
re-derives what this person is allowed to see from the spec and their role —
the frontend is told what to draw, but it is never trusted about permissions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from app.ai.provider import get_provider
from app.deps import (
    CurrentAppSession,
    PublishedProject,
    SessionDep,
    live_spec_of,
)
from app.engine.executor import build_trigger_context, resume_run, start_run
from app.models import (
    Approval,
    ApprovalDecision,
    AppUser,
    Notification,
    Project,
    ProjectKind,
    RunStatus,
    WorkflowRun,
    utcnow,
)
from app.runtime.fields import coerce_record
from app.runtime.records import RecordStore
from app.security import (
    create_app_token,
    hash_password,
    password_problem,
    tokens_equal,
    verify_password,
)
from app.specs.catalog import RecordScope, ScreenType
from app.specs.schema import AppSpec, EntitySpec, ScreenSpec

router = APIRouter(prefix="/api/a/{slug}", tags=["runtime"])


# --------------------------------------------------------------------------
# Shapes
# --------------------------------------------------------------------------


class AppLoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str


class JoinRequest(BaseModel):
    token: str = Field(max_length=64)
    password: str


class SubmitRequest(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class DecideRequest(BaseModel):
    approved: bool
    note: str | None = Field(default=None, max_length=1000)


def _field_payload(field_spec) -> dict[str, Any]:
    return {
        "name": field_spec.name,
        "label": field_spec.label,
        "type": str(field_spec.type),
        "required": field_spec.required,
        "choices": list(field_spec.choices),
        "help_text": field_spec.help_text,
        "default": field_spec.default,
        "references": field_spec.references,
    }


def _visible_fields(spec: AppSpec, screen: ScreenSpec, entity: EntitySpec) -> list:
    if not screen.fields:
        return list(entity.fields)
    ordered = [entity.field(name) for name in screen.fields]
    return [f for f in ordered if f is not None]


def _nav_for(session_ctx) -> list[dict[str, Any]]:
    """The pages this person can open, in spec order."""
    return [
        {
            "key": screen.key,
            "title": screen.title,
            "type": str(screen.type),
            "icon": screen.icon,
        }
        for screen in session_ctx.spec.screens_for_role(session_ctx.role)
    ]


def _record_payload(record, fields, creators: dict[str, str], references) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field_spec in fields:
        raw = record.data.get(field_spec.name)
        lookup = references.get(field_spec.name, {})
        values[field_spec.name] = lookup.get(str(raw), raw) if lookup else raw

    return {
        "id": record.id,
        "values": values,
        "submitted_by": creators.get(record.created_by or "", None),
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }


# --------------------------------------------------------------------------
# Getting in
# --------------------------------------------------------------------------


@router.get("/info")
def app_info(project: PublishedProject) -> dict[str, Any]:
    """What a visitor can know before signing in — the name, and nothing else."""
    if project.kind != ProjectKind.APP:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="There is no app at this link."
        )
    spec = live_spec_of(project)
    return {
        "name": spec.name,
        "description": spec.description,
        "slug": project.slug,
    }


@router.post("/login")
def app_login(
    body: AppLoginRequest, project: PublishedProject, session: SessionDep
) -> dict[str, Any]:
    email = body.email.strip().lower()
    user = session.scalars(
        select(AppUser).where(
            AppUser.project_id == project.id, func.lower(AppUser.email) == email
        )
    ).first()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password do not match.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your access to this app has been turned off.",
        )

    return {
        "token": create_app_token(user.id, project.id, user.role),
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    }


@router.post("/join")
def accept_invite(
    body: JoinRequest, project: PublishedProject, session: SessionDep
) -> dict[str, Any]:
    """Set a password against an outstanding invite."""
    problem = password_problem(body.password)
    if problem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=problem)

    candidates = session.scalars(
        select(AppUser).where(
            AppUser.project_id == project.id, AppUser.invite_token.is_not(None)
        )
    ).all()

    # Compared in constant time so the token cannot be guessed a byte at a time.
    user = next(
        (u for u in candidates if u.invite_token and tokens_equal(u.invite_token, body.token)),
        None,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That invite link is not valid. Ask for a new one.",
        )

    user.password_hash = hash_password(body.password)
    user.invite_token = None
    user.invite_accepted_at = utcnow()
    session.commit()

    return {
        "token": create_app_token(user.id, project.id, user.role),
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
    }


@router.get("/me")
def app_me(ctx: CurrentAppSession) -> dict[str, Any]:
    role = ctx.spec.role(ctx.role)
    return {
        "app": {"name": ctx.spec.name, "slug": ctx.project.slug},
        "user": {
            "id": ctx.user.id,
            "name": ctx.user.name,
            "email": ctx.user.email,
            "role": ctx.role,
            "role_label": role.label if role else ctx.role,
            "is_admin": ctx.is_admin,
        },
        "nav": _nav_for(ctx),
    }


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------


@router.get("/screens/{key}")
def get_screen(
    key: str,
    ctx: CurrentAppSession,
    session: SessionDep,
    search: str | None = Query(default=None, max_length=100),
    sort: str | None = Query(default=None, max_length=48),
    descending: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Everything needed to draw one page, including its data."""
    screen = ctx.require_screen(key)
    entity = ctx.spec.entity(screen.entity)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This page points at something that no longer exists.",
        )

    fields = _visible_fields(ctx.spec, screen, entity)
    payload: dict[str, Any] = {
        "key": screen.key,
        "title": screen.title,
        "type": str(screen.type),
        "entity": {"name": entity.name, "label": entity.label, "plural": entity.label_plural},
        "fields": [_field_payload(f) for f in fields],
        "empty_text": screen.empty_text,
        "title_field": entity.title_field.name,
    }

    if screen.type is ScreenType.FORM:
        payload["submit_workflow"] = screen.submit_workflow
        return payload

    store = RecordStore(session, ctx.project.id, ctx.spec)

    # An admin sees everything; everyone else is held to the screen's scope.
    scope = RecordScope.ALL if ctx.is_admin else screen.record_scope

    if screen.type is ScreenType.APPROVALS:
        return payload | _approvals_payload(ctx, session, screen, entity, fields, store)

    page = store.list(
        entity.name,
        scope=scope,
        app_user_id=ctx.user.id,
        filters=dict(screen.filters),
        search=search,
        sort_field=sort,
        descending=descending,
        limit=limit,
        offset=offset,
    )
    creators = store.creator_names(page.rows)
    references = store.resolve_references(entity.name, page.rows)

    payload["records"] = [
        _record_payload(row, fields, creators, references) for row in page.rows
    ]
    payload["total"] = page.total
    payload["has_more"] = page.has_more
    payload["scope"] = str(scope)
    return payload


def _approvals_payload(
    ctx, session: SessionDep, screen, entity, fields, store: RecordStore
) -> dict[str, Any]:
    """The queue of things waiting on this person's role."""
    roles = [r.name for r in ctx.spec.roles] if ctx.is_admin else [ctx.role]

    approvals = session.scalars(
        select(Approval)
        .where(
            Approval.project_id == ctx.project.id,
            Approval.role.in_(roles),
            Approval.decision == ApprovalDecision.PENDING,
            Approval.entity_name == entity.name,
        )
        .order_by(Approval.created_at)
    ).all()

    items = []
    for approval in approvals:
        record = (
            store.get(entity.name, approval.record_id) if approval.record_id else None
        )
        if record is None:
            continue  # the record was deleted; nothing to decide on
        creators = store.creator_names([record])
        references = store.resolve_references(entity.name, [record])
        items.append(
            {
                "approval_id": approval.id,
                "prompt": approval.prompt,
                "role": approval.role,
                "waiting_since": approval.created_at.isoformat(),
                "record": _record_payload(record, fields, creators, references),
            }
        )

    return {"approvals": items, "total": len(items)}


@router.get("/records/{entity_name}/{record_id}")
def get_record(
    entity_name: str, record_id: str, ctx: CurrentAppSession, session: SessionDep
) -> dict[str, Any]:
    """One record in full — but only if a screen this person has grants it."""
    entity = ctx.spec.entity(entity_name)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That does not exist."
        )

    allowed = [
        screen
        for screen in ctx.spec.screens_for_role(ctx.role)
        if screen.entity == entity_name and screen.type is not ScreenType.FORM
    ]
    if not allowed and not ctx.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to these records.",
        )

    store = RecordStore(session, ctx.project.id, ctx.spec)
    record = store.get(entity_name, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That record was not found."
        )

    # If every screen granting this entity is own-scope, this must be theirs.
    if not ctx.is_admin and all(s.record_scope is RecordScope.OWN for s in allowed):
        if record.created_by != ctx.user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only open records you submitted.",
            )

    creators = store.creator_names([record])
    references = store.resolve_references(entity_name, [record])
    return {
        "entity": {"name": entity.name, "label": entity.label},
        "fields": [_field_payload(f) for f in entity.fields],
        "record": _record_payload(record, list(entity.fields), creators, references),
    }


# --------------------------------------------------------------------------
# Submitting a form — the thing that starts a workflow
# --------------------------------------------------------------------------


@router.post("/screens/{key}/submit", status_code=status.HTTP_201_CREATED)
def submit_form(
    key: str, body: SubmitRequest, ctx: CurrentAppSession, session: SessionDep
) -> dict[str, Any]:
    screen = ctx.require_screen(key)
    if screen.type is not ScreenType.FORM:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="That page is not a form."
        )

    entity = ctx.spec.entity(screen.entity)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This form points at something that no longer exists.",
        )

    # The form's own field list is the allowlist. A crafted request cannot set
    # `status` when the form never offered it.
    coerced = coerce_record(entity, body.data, allowed_fields=list(screen.fields) or None)
    if not coerced.ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "Please check the form.", "field_errors": coerced.errors},
        )

    store = RecordStore(session, ctx.project.id, ctx.spec)
    record = store.create(entity.name, coerced.data, created_by=ctx.user.id)

    result: dict[str, Any] = {"record_id": record.id, "workflow": None}

    if screen.submit_workflow:
        workflow = ctx.spec.workflow(screen.submit_workflow)
        if workflow is not None:
            from app.engine.steps import RunEnv
            from app.engine.executor import run_summary

            env = RunEnv(
                spec=ctx.spec,
                project_id=ctx.project.id,
                records=store,
                session=session,
                classifier=get_provider().classify,
            )
            context = build_trigger_context(
                entity_name=entity.name,
                record_id=record.id,
                data=coerced.data,
                user={
                    "id": ctx.user.id,
                    "email": ctx.user.email,
                    "name": ctx.user.name,
                    "role": ctx.role,
                },
            )
            run = start_run(env, workflow, context, session=session)
            result["workflow"] = run_summary(run.run, run.steps)

    session.commit()
    return result


# --------------------------------------------------------------------------
# Deciding
# --------------------------------------------------------------------------


@router.post("/approvals/{approval_id}")
def decide(
    approval_id: str, body: DecideRequest, ctx: CurrentAppSession, session: SessionDep
) -> dict[str, Any]:
    """Approve or reject, then let the run carry on from where it paused."""
    approval = session.get(Approval, approval_id)
    if approval is None or approval.project_id != ctx.project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That item was not found."
        )

    if not ctx.is_admin and approval.role != ctx.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This is not waiting on you.",
        )

    if approval.decision != ApprovalDecision.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This has already been decided.",
        )

    run = session.get(WorkflowRun, approval.run_id)
    if run is None or run.status != RunStatus.WAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The workflow for this item is no longer waiting.",
        )

    from app.engine.steps import RunEnv
    from app.engine.executor import WorkflowError, run_summary

    env = RunEnv(
        spec=ctx.spec,
        project_id=ctx.project.id,
        records=RecordStore(session, ctx.project.id, ctx.spec),
        session=session,
        classifier=get_provider().classify,
    )

    try:
        result = resume_run(
            env,
            run,
            approved=body.approved,
            session=session,
            decided_by=ctx.user.id,
            note=body.note,
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {
        "decision": "approved" if body.approved else "rejected",
        "run": run_summary(result.run),
    }


# --------------------------------------------------------------------------
# Notifications
# --------------------------------------------------------------------------


@router.get("/notifications")
def list_notifications(
    ctx: CurrentAppSession,
    session: SessionDep,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    rows = session.scalars(
        select(Notification)
        .where(
            Notification.project_id == ctx.project.id,
            Notification.app_user_id == ctx.user.id,
        )
        .order_by(desc(Notification.created_at))
        .limit(limit)
    ).all()

    return {
        "unread": sum(1 for row in rows if row.read_at is None),
        "notifications": [
            {
                "id": row.id,
                "title": row.title,
                "body": row.body,
                "read": row.read_at is not None,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }


@router.post("/notifications/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(ctx: CurrentAppSession, session: SessionDep) -> None:
    rows = session.scalars(
        select(Notification).where(
            Notification.project_id == ctx.project.id,
            Notification.app_user_id == ctx.user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    for row in rows:
        row.read_at = utcnow()
    session.commit()


# --------------------------------------------------------------------------
# Published websites
# --------------------------------------------------------------------------

site_router = APIRouter(prefix="/api/s", tags=["sites"])


@site_router.get("/{slug}")
def get_site(slug: str, session: SessionDep) -> dict[str, Any]:
    """A published site's content. Public — no token, no login."""
    project = session.scalars(select(Project).where(Project.slug == slug)).first()
    if project is None or project.kind != ProjectKind.SITE or not project.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="There is no site at this link."
        )

    return {
        "slug": project.slug,
        "name": project.name,
        "spec": project.published_spec,
        "files": project.published_files,
        "published_at": project.published_at.isoformat() if project.published_at else None,
    }
