"""Builder routes: plan, build, edit, test, publish.

These are the routes the dashboard calls. They all act on the *draft* spec, so
nothing an owner does here changes what their staff see until they publish.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from app.ai.planner import PlanningError, plan_app, plan_site, revise_app
from app.ai.provider import AIError
from app.ai.site_agents import build_custom_site
from app.config import get_settings
from app.deps import CurrentUser, OwnedApp, OwnedProject, SessionDep, draft_spec_of
from app.engine.executor import build_trigger_context, run_summary, start_run
from app.engine.steps import RunEnv
from app.models import (
    AppUser,
    Project,
    ProjectKind,
    ProjectStatus,
    SiteRevision,
    UsageEvent,
    WorkflowRun,
    utcnow,
)
from app.runtime.memory_store import MemoryRecordStore
from app.runtime.records import RecordStore
from app.sites.codebuild import SiteBuildError, build_site_files
from app.sites.templates import SITE_TEMPLATES, SITE_THEMES
from app.specs.catalog import RESERVED_SLUGS
from app.specs.describe import describe_plan
from app.specs.loader import TemplateNotFound, list_templates, load_template
from app.specs.schema import AppSpec, SiteSpec
from app.specs.validator import validate_app_spec

router = APIRouter(prefix="/api", tags=["projects"])
settings = get_settings()


# --------------------------------------------------------------------------
# Shapes
# --------------------------------------------------------------------------


class PlanRequest(BaseModel):
    description: str = Field(min_length=5, max_length=4000)


class CreateFromPlanRequest(BaseModel):
    kind: Literal["app", "site"] = "app"
    name: str | None = Field(default=None, max_length=120)
    source_prompt: str | None = Field(default=None, max_length=4000)
    spec: dict[str, Any]
    files: dict[str, str] | None = None


class CreateFromTemplateRequest(BaseModel):
    template: str


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=48)
    spec: dict[str, Any] | None = None
    files: dict[str, str] | None = None


class ReviseRequest(BaseModel):
    instruction: str = Field(min_length=3, max_length=1000)


class TestRunRequest(BaseModel):
    workflow_key: str
    data: dict[str, Any] = Field(default_factory=dict)
    #: What the approver decides during the test.
    approve: bool = True


def _project_payload(project: Project, *, with_spec: bool = False) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": project.id,
        "kind": project.kind,
        "name": project.name,
        "slug": project.slug,
        "status": project.status,
        "is_published": project.is_published,
        "source_prompt": project.source_prompt,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
        "published_at": project.published_at.isoformat() if project.published_at else None,
        "public_path": f"/{'a' if project.kind == ProjectKind.APP else 's'}/{project.slug}",
    }
    if with_spec:
        payload["spec"] = project.draft_spec
        payload["files"] = project.draft_files
        payload["has_unpublished_changes"] = (
            project.is_published and (
                project.draft_spec != project.published_spec
                or project.draft_files != project.published_files
            )
        )
    return payload


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:38]
    return slug or "app"


def _unique_slug(session: SessionDep, desired: str) -> str:
    base = _slugify(desired)
    if base in RESERVED_SLUGS:
        base = f"{base}-app"

    candidate, suffix = base, 1
    while (
        candidate in RESERVED_SLUGS
        or session.scalars(select(Project.id).where(Project.slug == candidate)).first()
    ):
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


def _record_usage(
    session: SessionDep,
    user_id: str,
    kind: str,
    result: Any,
    project_id: str | None = None,
) -> None:
    """Log what a generation cost. Shown to nobody yet; measured from day one."""
    session.add(
        UsageEvent(
            user_id=user_id,
            project_id=project_id,
            kind=kind,
            provider=getattr(result, "provider", None),
            model=getattr(result, "model", None),
            input_tokens=getattr(result, "input_tokens", 0),
            output_tokens=getattr(result, "output_tokens", 0),
            cost_micros=getattr(result, "cost_micros", 0),
        )
    )


def _check_project_limit(session: SessionDep, user: CurrentUser) -> None:
    count = (
        session.scalar(
            select(func.count()).select_from(
                select(Project.id).where(Project.owner_id == user.id).subquery()
            )
        )
        or 0
    )
    if count >= settings.max_projects_per_user:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"You have reached the limit of {settings.max_projects_per_user} "
                "projects. Delete one to make room."
            ),
        )


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------


@router.get("/templates")
def get_templates() -> dict[str, Any]:
    return {
        "apps": list_templates(),
        "sites": [
            {"key": key, "name": t["name"], "blurb": t["blurb"]}
            for key, t in SITE_TEMPLATES.items()
        ],
        "themes": list(SITE_THEMES),
    }


# --------------------------------------------------------------------------
# Planning — no project is created, so the user can look before committing
# --------------------------------------------------------------------------


@router.post("/plan/app")
def plan_an_app(body: PlanRequest, session: SessionDep, user: CurrentUser) -> dict[str, Any]:
    try:
        result = plan_app(body.description, allow_template_fallback=False)
    except PlanningError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except AIError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    _record_usage(session, user.id, "generation", result)
    session.commit()

    return {
        "spec": result.spec.model_dump(mode="json"),
        "plan": describe_plan(result.spec),
        "warnings": result.report.to_dict()["warnings"],
        "offline": result.offline,
        "fallback_reason": result.fallback_reason,
        "attempts": result.attempts,
    }


@router.post("/plan/site")
def plan_a_site(body: PlanRequest, session: SessionDep, user: CurrentUser) -> dict[str, Any]:
    try:
        result = plan_site(
            body.description,
            templates=list(SITE_TEMPLATES),
            themes=list(SITE_THEMES),
        )
    except PlanningError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except AIError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    _record_usage(session, user.id, "generation", result)
    session.commit()

    return {"spec": result.spec.model_dump(mode="json"), "offline": result.offline}


@router.post("/plan/site/custom")
def plan_custom_site(body: PlanRequest, session: SessionDep, user: CurrentUser) -> dict[str, Any]:
    """Run product, design, code, review and compile stages for a custom site."""
    _check_project_limit(session, user)
    recent_generations = session.scalar(
        select(func.count()).select_from(UsageEvent).where(
            UsageEvent.user_id == user.id,
            UsageEvent.created_at >= utcnow() - timedelta(hours=24),
            UsageEvent.kind.in_(["generation", "custom_site_generation"]),
        )
    ) or 0
    if recent_generations >= settings.max_generations_per_day:
        raise HTTPException(status_code=429, detail="You have reached today's website and workflow generation limit. Try again tomorrow.")
    usage_event = UsageEvent(user_id=user.id, kind="custom_site_generation")
    session.add(usage_event)
    session.commit()
    try:
        result = build_custom_site(body.description)
    except AIError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    usage_event.provider = result.provider[:32]
    usage_event.model = result.model[:64]
    usage_event.input_tokens = result.input_tokens
    usage_event.output_tokens = result.output_tokens
    usage_event.cost_micros = result.cost_micros
    session.commit()
    return {
        "spec": result.spec.model_dump(mode="json"),
        "files": {name: result.files[name] for name in ("App.tsx", "styles.css")},
        "agents": result.agent_log,
        "offline": False,
    }


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------


@router.get("/projects")
def list_projects(session: SessionDep, user: CurrentUser) -> dict[str, Any]:
    projects = session.scalars(
        select(Project)
        .where(Project.owner_id == user.id)
        .order_by(desc(Project.updated_at))
    ).all()
    return {"projects": [_project_payload(p) for p in projects]}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    body: CreateFromPlanRequest, session: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    """Build the thing the user just approved a plan for."""
    _check_project_limit(session, user)

    if body.kind == "app":
        spec = _validated_app_spec(body.spec)
        name = body.name or spec.name
    else:
        try:
            site = SiteSpec.model_validate(body.spec)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"That site configuration is not valid: {exc}",
            ) from exc
        name = body.name or site.site_name

    compiled_files = None
    if body.files is not None:
        if body.kind != "site":
            raise HTTPException(status_code=422, detail="Code files are only available for websites.")
        try:
            compiled_files = build_site_files(body.files)
        except SiteBuildError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    project = Project(
        owner_id=user.id,
        kind=ProjectKind.APP if body.kind == "app" else ProjectKind.SITE,
        name=name[:120],
        slug=_unique_slug(session, name),
        status=ProjectStatus.DRAFT,
        source_prompt=body.source_prompt,
        draft_spec=body.spec,
        draft_files=compiled_files,
    )
    session.add(project)
    session.commit()

    if compiled_files:
        session.add(SiteRevision(
            project_id=project.id, version=1, label="First AI build",
            prompt=body.source_prompt, spec=body.spec, files=compiled_files,
        ))
        session.commit()

    return _project_payload(project, with_spec=True)


@router.post("/projects/from-template", status_code=status.HTTP_201_CREATED)
def create_from_template(
    body: CreateFromTemplateRequest, session: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    _check_project_limit(session, user)
    try:
        spec = load_template(body.template)
    except TemplateNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    project = Project(
        owner_id=user.id,
        kind=ProjectKind.APP,
        name=spec.name,
        slug=_unique_slug(session, spec.name),
        status=ProjectStatus.DRAFT,
        source_prompt=f"Started from the {body.template} template",
        draft_spec=spec.model_dump(mode="json"),
    )
    session.add(project)
    session.commit()
    return _project_payload(project, with_spec=True)


@router.get("/projects/{project_id}")
def get_project(project: OwnedProject) -> dict[str, Any]:
    payload = _project_payload(project, with_spec=True)
    if project.kind == ProjectKind.APP and project.draft_spec:
        spec = draft_spec_of(project)
        payload["plan"] = describe_plan(spec)
    return payload


@router.patch("/projects/{project_id}")
def update_project(
    body: UpdateProjectRequest, project: OwnedProject, session: SessionDep
) -> dict[str, Any]:
    previous_spec = project.draft_spec
    previous_files = project.draft_files
    if body.name is not None:
        project.name = body.name.strip()[:120]

    if body.slug is not None:
        desired = _slugify(body.slug)
        if desired != project.slug:
            if desired in RESERVED_SLUGS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{desired}' is reserved. Please pick another link.",
                )
            taken = session.scalars(
                select(Project.id).where(
                    Project.slug == desired, Project.id != project.id
                )
            ).first()
            if taken:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"The link '{desired}' is already taken.",
                )
            project.slug = desired

    if body.spec is not None:
        if project.kind == ProjectKind.APP:
            _validated_app_spec(body.spec)
        else:
            try:
                SiteSpec.model_validate(body.spec)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
                ) from exc
        project.draft_spec = body.spec

    if body.files is not None:
        if project.kind != ProjectKind.SITE:
            raise HTTPException(status_code=422, detail="Code files are only available for websites.")
        try:
            project.draft_files = build_site_files(body.files)
        except SiteBuildError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    if project.draft_files and (
        previous_spec != project.draft_spec or previous_files != project.draft_files
    ):
        latest = session.scalar(
            select(func.max(SiteRevision.version)).where(SiteRevision.project_id == project.id)
        ) or 0
        session.add(SiteRevision(
            project_id=project.id,
            version=latest + 1,
            label="Saved changes",
            prompt=project.source_prompt,
            spec=project.draft_spec or {},
            files=project.draft_files,
        ))

    project.updated_at = utcnow()
    session.commit()
    return _project_payload(project, with_spec=True)


@router.get("/projects/{project_id}/revisions")
def list_site_revisions(project: OwnedProject, session: SessionDep) -> dict[str, Any]:
    if project.kind != ProjectKind.SITE:
        raise HTTPException(status_code=404, detail="This project has no website revisions.")
    revisions = session.scalars(
        select(SiteRevision)
        .where(SiteRevision.project_id == project.id)
        .order_by(desc(SiteRevision.version))
    ).all()
    return {"revisions": [{
        "id": item.id,
        "version": item.version,
        "label": item.label,
        "prompt": item.prompt,
        "created_at": item.created_at.isoformat(),
    } for item in revisions]}


@router.post("/projects/{project_id}/revisions/{revision_id}/restore")
def restore_site_revision(
    revision_id: str, project: OwnedProject, session: SessionDep
) -> dict[str, Any]:
    if project.kind != ProjectKind.SITE:
        raise HTTPException(status_code=404, detail="This project has no website revisions.")
    revision = session.scalars(select(SiteRevision).where(
        SiteRevision.id == revision_id,
        SiteRevision.project_id == project.id,
    )).first()
    if revision is None:
        raise HTTPException(status_code=404, detail="That saved version could not be found.")
    project.draft_spec = revision.spec
    project.draft_files = revision.files
    latest = session.scalar(
        select(func.max(SiteRevision.version)).where(SiteRevision.project_id == project.id)
    ) or 0
    session.add(SiteRevision(
        project_id=project.id,
        version=latest + 1,
        label=f"Restored version {revision.version}",
        prompt=revision.prompt,
        spec=revision.spec,
        files=revision.files,
    ))
    project.updated_at = utcnow()
    session.commit()
    return _project_payload(project, with_spec=True)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project: OwnedProject, session: SessionDep) -> None:
    session.delete(project)
    session.commit()


def _validated_app_spec(payload: dict[str, Any]) -> AppSpec:
    """Parse and validate, or refuse. Nothing invalid is ever stored."""
    try:
        spec = AppSpec.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"That configuration is not valid: {exc}",
        ) from exc

    report = validate_app_spec(spec)
    if not report.ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "That configuration has problems that must be fixed first.",
                **report.to_dict(),
            },
        )
    return spec


# --------------------------------------------------------------------------
# Editing with words
# --------------------------------------------------------------------------


@router.post("/projects/{project_id}/revise")
def revise(
    body: ReviseRequest, project: OwnedApp, session: SessionDep, user: CurrentUser
) -> dict[str, Any]:
    """Propose a change. Nothing is saved — the user sees it and decides."""
    current = draft_spec_of(project)
    try:
        result = revise_app(current, body.instruction)
    except PlanningError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except AIError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    _record_usage(session, user.id, "generation", result, project.id)
    session.commit()

    return {
        "spec": result.spec.model_dump(mode="json"),
        "plan": describe_plan(result.spec),
        "before": describe_plan(current),
        "warnings": result.report.to_dict()["warnings"],
    }


# --------------------------------------------------------------------------
# Publishing
# --------------------------------------------------------------------------


@router.post("/projects/{project_id}/publish")
def publish(project: OwnedProject, session: SessionDep) -> dict[str, Any]:
    if not project.draft_spec:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is nothing to publish yet.",
        )

    if project.kind == ProjectKind.APP:
        _validated_app_spec(project.draft_spec)
    else:
        try:
            SiteSpec.model_validate(project.draft_spec)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"That site configuration is not valid: {exc}") from exc

    # Freeze a copy. Editing the draft afterwards does not change what is live.
    project.published_spec = project.draft_spec
    project.published_files = project.draft_files
    project.status = ProjectStatus.PUBLISHED
    project.published_at = utcnow()
    session.commit()

    return _project_payload(project, with_spec=True)


@router.post("/projects/{project_id}/unpublish")
def unpublish(project: OwnedProject, session: SessionDep) -> dict[str, Any]:
    project.status = ProjectStatus.DRAFT
    project.published_spec = None
    project.published_files = None
    project.published_at = None
    session.commit()
    return _project_payload(project, with_spec=True)


# --------------------------------------------------------------------------
# Testing a workflow
# --------------------------------------------------------------------------


@router.post("/projects/{project_id}/test-run")
def test_run(
    body: TestRunRequest, project: OwnedApp, session: SessionDep
) -> dict[str, Any]:
    """Run a workflow for real, against data that is thrown away.

    This is the feature that earns trust: the conditions, branches and
    approvals all execute, and the user watches each step pass.
    """
    spec = draft_spec_of(project)
    workflow = spec.workflow(body.workflow_key)
    if workflow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"There is no workflow called '{body.workflow_key}'.",
        )

    entity = spec.entity(workflow.trigger.entity)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This workflow's trigger points at something that no longer exists.",
        )

    from app.ai.provider import get_provider
    from app.runtime.fields import coerce_record

    coerced = coerce_record(entity, body.data, require_required=False)

    memory = MemoryRecordStore(project_id=project.id)
    record = memory.create(entity.name, coerced.data)

    provider = get_provider()
    env = RunEnv(
        spec=spec,
        project_id=project.id,
        records=memory,
        session=session,
        classifier=provider.classify,
        is_test=True,
        test_approves=body.approve,
    )

    context = build_trigger_context(
        entity_name=entity.name,
        record_id=record.id,
        data=coerced.data,
        user={
            "id": "test-user",
            "email": "test@example.com",
            "name": "Test person",
            "role": spec.roles[0].name,
        },
    )

    result = start_run(env, workflow, context, session=session)

    # A test leaves nothing behind, including its own run row.
    session.rollback()

    return {
        "run": run_summary(result.run, result.steps),
        "records": memory.snapshot(),
        "notifications": env.captured_notifications,
        "emails": env.captured_emails,
        "field_errors": coerced.errors,
    }


# --------------------------------------------------------------------------
# Run history
# --------------------------------------------------------------------------


@router.get("/projects/{project_id}/runs")
def list_runs(
    project: OwnedApp,
    session: SessionDep,
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    runs = session.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.project_id == project.id, WorkflowRun.is_test.is_(False))
        .order_by(desc(WorkflowRun.sequence))
        .limit(limit)
    ).all()
    return {"runs": [run_summary(run) for run in runs]}


@router.get("/projects/{project_id}/runs/{run_id}")
def get_run(run_id: str, project: OwnedApp, session: SessionDep) -> dict[str, Any]:
    run = session.get(WorkflowRun, run_id)
    if run is None or run.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That run was not found."
        )
    return run_summary(run)


# --------------------------------------------------------------------------
# The app's own users
# --------------------------------------------------------------------------


class InviteRequest(BaseModel):
    email: str = Field(max_length=255)
    name: str = Field(min_length=1, max_length=120)
    role: str


@router.get("/projects/{project_id}/members")
def list_members(project: OwnedApp, session: SessionDep) -> dict[str, Any]:
    spec = draft_spec_of(project)
    members = session.scalars(
        select(AppUser)
        .where(AppUser.project_id == project.id)
        .order_by(AppUser.created_at)
    ).all()

    return {
        "roles": [
            {"name": r.name, "label": r.label, "is_admin": r.is_admin} for r in spec.roles
        ],
        "members": [
            {
                "id": m.id,
                "email": m.email,
                "name": m.name,
                "role": m.role,
                "is_active": m.is_active,
                "pending_invite": m.is_pending_invite,
                "invite_token": m.invite_token if m.is_pending_invite else None,
            }
            for m in members
        ],
    }


@router.post(
    "/projects/{project_id}/members", status_code=status.HTTP_201_CREATED
)
def invite_member(
    body: InviteRequest, project: OwnedApp, session: SessionDep
) -> dict[str, Any]:
    from app.models import new_token

    spec = draft_spec_of(project)
    if spec.role(body.role) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{body.role}' is not a role in this app.",
        )

    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="That is not an email address."
        )

    existing = session.scalars(
        select(AppUser).where(
            AppUser.project_id == project.id, func.lower(AppUser.email) == email
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{email} is already a member of this app.",
        )

    member = AppUser(
        project_id=project.id,
        email=email,
        name=body.name.strip(),
        role=body.role,
        invite_token=new_token(),
    )
    session.add(member)
    session.commit()

    return {
        "id": member.id,
        "email": member.email,
        "name": member.name,
        "role": member.role,
        "pending_invite": True,
        "invite_token": member.invite_token,
        "invite_path": f"/a/{project.slug}/join?token={member.invite_token}",
    }


@router.delete(
    "/projects/{project_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT
)
def remove_member(member_id: str, project: OwnedApp, session: SessionDep) -> None:
    member = session.get(AppUser, member_id)
    if member is None or member.project_id != project.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That member was not found."
        )
    session.delete(member)
    session.commit()


# --------------------------------------------------------------------------
# Usage
# --------------------------------------------------------------------------


@router.get("/usage")
def usage(session: SessionDep, user: CurrentUser) -> dict[str, Any]:
    rows = session.execute(
        select(
            UsageEvent.kind,
            func.count(UsageEvent.id),
            func.sum(UsageEvent.input_tokens),
            func.sum(UsageEvent.output_tokens),
            func.sum(UsageEvent.cost_micros),
        )
        .where(UsageEvent.user_id == user.id)
        .group_by(UsageEvent.kind)
    ).all()

    return {
        "by_kind": {
            kind: {
                "count": count,
                "input_tokens": int(input_tokens or 0),
                "output_tokens": int(output_tokens or 0),
                "cost_rupees": round((cost or 0) / 1_000_000, 4),
            }
            for kind, count, input_tokens, output_tokens, cost in rows
        },
        "limits": {
            "projects": settings.max_projects_per_user,
            "runs_per_month": settings.max_runs_per_month,
        },
    }
