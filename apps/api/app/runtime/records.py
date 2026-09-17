"""Tenant-scoped access to generated-app data.

Everything that touches the `records` table goes through `RecordStore`. The
store cannot be built without a project id, and every query it issues filters
on that id. That is the whole point: there is no code path that reads records
without saying whose records they are, so there is no code path that can
forget.

Nothing else in the codebase may query `Record` directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, false, func, or_, select
from sqlalchemy.orm import Session

from app.models import AppUser, Record
from app.specs.catalog import FieldType, RecordScope
from app.specs.schema import AppSpec, EntitySpec


class RecordNotFound(LookupError):
    """The record does not exist, or belongs to a different project."""


@dataclass(frozen=True)
class Page:
    rows: list[Record]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.rows) < self.total


class RecordStore:
    """Reads and writes one project's records. Scope is not optional."""

    #: Field types whose value is an opaque id, so searching them is pointless.
    _UNSEARCHABLE = frozenset({FieldType.REFERENCE, FieldType.USER, FieldType.BOOLEAN})

    def __init__(self, session: Session, project_id: str, spec: AppSpec | None = None):
        if not project_id:
            raise ValueError("RecordStore requires a project_id")
        self.session = session
        self.project_id = project_id
        self.spec = spec

    # -- internals --------------------------------------------------------

    def _base(self, entity_name: str) -> Select[tuple[Record]]:
        """Every query starts here, so every query is scoped."""
        return select(Record).where(
            Record.project_id == self.project_id,
            Record.entity_name == entity_name,
        )

    def _entity(self, entity_name: str) -> EntitySpec | None:
        return self.spec.entity(entity_name) if self.spec else None

    # -- reads ------------------------------------------------------------

    def get(self, entity_name: str, record_id: str) -> Record | None:
        return self.session.scalars(
            self._base(entity_name).where(Record.id == record_id)
        ).first()

    def require(self, entity_name: str, record_id: str) -> Record:
        record = self.get(entity_name, record_id)
        if record is None:
            raise RecordNotFound(f"no '{entity_name}' record {record_id} in this app")
        return record

    def get_any_entity(self, record_id: str) -> Record | None:
        """Fetch by id alone, still scoped to this project.

        Used where the entity is implied by the record itself, such as
        resolving an approval's subject.
        """
        return self.session.scalars(
            select(Record).where(
                Record.project_id == self.project_id, Record.id == record_id
            )
        ).first()

    def list(
        self,
        entity_name: str,
        *,
        scope: RecordScope = RecordScope.ALL,
        app_user_id: str | None = None,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        sort_field: str | None = None,
        descending: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Page:
        query = self._base(entity_name)

        if scope is RecordScope.OWN:
            # Without a user, "own records" is the empty set. Comparing to None
            # would compile to `IS NULL` and match every record a workflow
            # created, which is the opposite of what own-scope means.
            if app_user_id is None:
                return Page(rows=[], total=0, limit=limit, offset=offset)
            query = query.where(Record.created_by == app_user_id)

        for key, value in (filters or {}).items():
            query = query.where(Record.data[key].as_string() == str(value))

        if search:
            query = query.where(self._search_clause(entity_name, search))

        total = (
            self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        )

        if sort_field:
            column = Record.data[sort_field].as_string()
            query = query.order_by(column.desc() if descending else column.asc())
        else:
            query = query.order_by(
                Record.created_at.desc() if descending else Record.created_at.asc()
            )

        rows = list(
            self.session.scalars(query.limit(max(1, min(limit, 200))).offset(max(0, offset)))
        )
        return Page(rows=rows, total=total, limit=limit, offset=offset)

    def _search_clause(self, entity_name: str, search: str):
        """Match `search` against every field worth searching."""
        entity = self._entity(entity_name)
        if entity is None:
            # Without the spec we cannot know which keys hold text. Guessing
            # would either miss rows or leak them, so refuse instead.
            raise ValueError(
                f"cannot search '{entity_name}' without a spec on the RecordStore"
            )

        searchable = [f.name for f in entity.fields if f.type not in self._UNSEARCHABLE]
        if not searchable:
            return false()

        pattern = f"%{search.strip()}%"
        return or_(
            *(Record.data[name].as_string().ilike(pattern) for name in searchable)
        )

    def count(self, entity_name: str, filters: dict[str, Any] | None = None) -> int:
        query = self._base(entity_name)
        for key, value in (filters or {}).items():
            query = query.where(Record.data[key].as_string() == str(value))
        return self.session.scalar(select(func.count()).select_from(query.subquery())) or 0

    # -- writes -----------------------------------------------------------

    def create(
        self, entity_name: str, data: dict[str, Any], *, created_by: str | None = None
    ) -> Record:
        record = Record(
            project_id=self.project_id,
            entity_name=entity_name,
            data=dict(data),
            created_by=created_by,
        )
        self.session.add(record)
        self.session.flush()  # so callers get the id without committing
        return record

    def update(self, entity_name: str, record_id: str, values: dict[str, Any]) -> Record:
        record = self.require(entity_name, record_id)
        # Replace the dict rather than mutating it: SQLAlchemy does not track
        # in-place changes to a JSON column, so a mutation would not be saved.
        record.data = {**record.data, **values}
        self.session.flush()
        return record

    def delete(self, entity_name: str, record_id: str) -> None:
        self.session.delete(self.require(entity_name, record_id))
        self.session.flush()

    # -- presentation helpers ---------------------------------------------

    def creator_names(self, records: list[Record]) -> dict[str, str]:
        """Map app_user id -> name, for showing who submitted what."""
        ids = {r.created_by for r in records if r.created_by}
        if not ids:
            return {}
        users = self.session.scalars(
            select(AppUser).where(
                AppUser.project_id == self.project_id, AppUser.id.in_(ids)
            )
        ).all()
        return {u.id: u.name for u in users}

    def resolve_references(
        self, entity_name: str, records: list[Record]
    ) -> dict[str, dict[str, str]]:
        """Titles for referenced records, so a table shows a name not an id.

        Returns `{field_name: {record_id: title}}`.
        """
        entity = self._entity(entity_name)
        if entity is None or self.spec is None:
            return {}

        resolved: dict[str, dict[str, str]] = {}
        for field_spec in entity.fields:
            if field_spec.type is not FieldType.REFERENCE or not field_spec.references:
                continue

            target = self.spec.entity(field_spec.references)
            if target is None:
                continue

            ids = {
                str(r.data.get(field_spec.name))
                for r in records
                if r.data.get(field_spec.name)
            }
            if not ids:
                continue

            title_field = target.title_field.name
            rows = self.session.scalars(
                self._base(field_spec.references).where(Record.id.in_(ids))
            ).all()
            resolved[field_spec.name] = {
                row.id: str(row.data.get(title_field, row.id)) for row in rows
            }

        return resolved
