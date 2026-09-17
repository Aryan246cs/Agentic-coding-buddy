"""Shared test fixtures.

Every test runs against a fresh in-memory SQLite database, so tests never see
each other's rows and never touch the development database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    AppUser,
    Base,
    Project,
    ProjectKind,
    ProjectStatus,
    User,
)
from app.runtime.records import RecordStore
from app.specs.schema import AppSpec

DEMOS = Path(__file__).resolve().parents[1] / "demos"


def load_demo(name: str) -> AppSpec:
    return AppSpec.model_validate(json.loads((DEMOS / f"{name}.json").read_text()))


@pytest.fixture(scope="session")
def demo_specs() -> dict[str, AppSpec]:
    return {path.stem: load_demo(path.stem) for path in sorted(DEMOS.glob("*.json"))}


@pytest.fixture(autouse=True)
def never_call_a_real_model():
    """No test may reach a live AI provider.

    Seeding the provider cache catches every call site at once, including the
    routers that import `get_provider` by name at module load. A test suite
    that quietly spends money — or fails when the network is down — is worse
    than no test suite.
    """
    from app.ai import provider as provider_module
    from app.config import get_settings

    previous = (provider_module._cache.instance, provider_module._cache.key)
    provider_module._cache.instance = provider_module.EchoProvider()
    provider_module._cache.key = get_settings().resolved_provider
    yield
    provider_module._cache.instance, provider_module._cache.key = previous


@pytest.fixture
def engine() -> Engine:
    # StaticPool keeps every connection pointed at the same in-memory database.
    # Without it each connection gets its own, and the test client — which runs
    # the app on another thread — would find no tables.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine: Engine) -> Session:
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as session:
        yield session


@pytest.fixture
def owner(session: Session) -> User:
    user = User(email="owner@example.com", name="Owner", password_hash="x")
    session.add(user)
    session.flush()
    return user


class AppFactory:
    """Builds a project from a demo spec, with app users for each role."""

    def __init__(self, session: Session, owner: User):
        self.session = session
        self.owner = owner
        self._slug = 0

    def build(
        self, spec: AppSpec, *, slug: str | None = None, published: bool = True
    ) -> tuple[Project, dict[str, AppUser]]:
        self._slug += 1
        project = Project(
            owner_id=self.owner.id,
            kind=ProjectKind.APP,
            name=spec.name,
            slug=slug or f"demo-{self._slug}",
            status=ProjectStatus.PUBLISHED if published else ProjectStatus.DRAFT,
            draft_spec=spec.model_dump(mode="json"),
            published_spec=spec.model_dump(mode="json") if published else None,
        )
        self.session.add(project)
        self.session.flush()

        users: dict[str, AppUser] = {}
        for role in spec.roles:
            user = AppUser(
                project_id=project.id,
                email=f"{role.name}@example.com",
                name=role.label,
                role=role.name,
                password_hash="x",
            )
            self.session.add(user)
            users[role.name] = user
        self.session.flush()

        return project, users


@pytest.fixture
def app_factory(session: Session, owner: User) -> AppFactory:
    return AppFactory(session, owner)


@pytest.fixture
def store_for(session: Session):
    def _make(project: Project, spec: AppSpec) -> RecordStore:
        return RecordStore(session, project.id, spec)

    return _make


def stub_classifier(answer: str):
    """A classifier that always returns `answer`, for deterministic tests."""

    def classify(text: str, categories: list[str]) -> str:  # noqa: ARG001
        return answer

    return classify


def step_log(result: Any) -> list[tuple[str, str]]:
    """`(step_id, status)` pairs, for asserting on the shape of a run."""
    return [(s.step_id, s.status) for s in result.steps]
