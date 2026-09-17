"""Request dependencies: who is asking, and what they are allowed to touch.

The two audiences never mix. A platform token identifies one of our customers
and is accepted only on `/api/...` builder routes. An app token identifies one
of *their* staff, carries the project it belongs to, and is accepted only on
that project's runtime routes.

Authorisation lives here and in the runtime router — never in the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import AppUser, Project, ProjectKind, User
from app.security import (
    PLATFORM_AUDIENCE,
    AuthError,
    app_audience,
    decode_token,
)
from app.specs.schema import AppSpec

SessionDep = Annotated[Session, Depends(get_session)]


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1].strip()


# --------------------------------------------------------------------------
# Platform (our customers)
# --------------------------------------------------------------------------


def current_user(
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = _bearer(authorization)
    try:
        payload = decode_token(token, PLATFORM_AUDIENCE)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    user = session.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="This account is not active."
        )
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def owned_project(
    project_id: Annotated[str, Path()],
    session: SessionDep,
    user: CurrentUser,
) -> Project:
    """A project the signed-in user owns.

    A project belonging to someone else reads as "not found" rather than
    "forbidden", so the API does not confirm that an id exists.
    """
    project = session.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="That project was not found."
        )
    return project


OwnedProject = Annotated[Project, Depends(owned_project)]


def owned_app(project: OwnedProject) -> Project:
    if project.kind != ProjectKind.APP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That project is a website, not an app.",
        )
    return project


OwnedApp = Annotated[Project, Depends(owned_app)]


# --------------------------------------------------------------------------
# Runtime (our customers' staff)
# --------------------------------------------------------------------------


def published_project(slug: Annotated[str, Path()], session: SessionDep) -> Project:
    """A project being served publicly by its slug."""
    project = session.scalars(select(Project).where(Project.slug == slug)).first()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="There is nothing at this link."
        )
    if not project.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This app has not been published yet.",
        )
    return project


PublishedProject = Annotated[Project, Depends(published_project)]


@dataclass
class AppSession:
    """An app user, the app they are in, and that app's live spec."""

    user: AppUser
    project: Project
    spec: AppSpec

    @property
    def role(self) -> str:
        return self.user.role

    @property
    def is_admin(self) -> bool:
        role = self.spec.role(self.user.role)
        return bool(role and role.is_admin)

    def require_screen(self, key: str):
        """The screen, if this user's role may open it.

        Checked server-side on every request. Hiding a link in the UI is
        cosmetic; this is the part that actually stops someone.
        """
        screen = self.spec.screen(key)
        if screen is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="That page does not exist."
            )
        if not self.is_admin and self.role not in screen.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to that page.",
            )
        return screen


def current_app_session(
    project: PublishedProject,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> AppSession:
    token = _bearer(authorization)
    try:
        payload = decode_token(token, app_audience(project.id))
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    app_user = session.get(AppUser, payload["sub"])
    if (
        app_user is None
        or app_user.project_id != project.id
        or not app_user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to this app again.",
        )

    spec = live_spec_of(project)

    # A role removed from the spec since this person was invited must not fall
    # back to seeing everything.
    if spec.role(app_user.role) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role no longer exists in this app. Ask the owner to re-invite you.",
        )

    return AppSession(user=app_user, project=project, spec=spec)


CurrentAppSession = Annotated[AppSession, Depends(current_app_session)]


def _parse_spec(payload: dict | None) -> AppSpec:
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This app has not been built yet.",
        )
    try:
        return AppSpec.model_validate(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="This app's configuration could not be read.",
        ) from exc


def live_spec_of(project: Project) -> AppSpec:
    """What visitors are served: the published copy, else the draft."""
    return _parse_spec(project.live_spec)


def draft_spec_of(project: Project) -> AppSpec:
    """What the owner is editing. Never the published copy.

    Builder routes act on the draft so that an edit is invisible to the app's
    users until Publish.
    """
    return _parse_spec(project.draft_spec)
