"""A record store that keeps everything in memory.

The Test button needs to run a real workflow — real conditions, real branching,
real expressions — without leaving anything behind. Swapping this in for
`RecordStore` gives exactly that: the engine cannot tell the difference, and
the database is never touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models import new_id


@dataclass
class MemoryRecord:
    """Stands in for a `Record` row. Same attributes the engine reads."""

    id: str
    entity_name: str
    data: dict[str, Any]
    created_by: str | None = None


@dataclass
class MemoryRecordStore:
    """In-memory `RecordSink`. Keeps insertion order so a test log reads well."""

    project_id: str = "test"
    rows: dict[str, MemoryRecord] = field(default_factory=dict)

    def create(
        self, entity_name: str, data: dict[str, Any], *, created_by: str | None = None
    ) -> MemoryRecord:
        record = MemoryRecord(
            id=new_id(), entity_name=entity_name, data=dict(data), created_by=created_by
        )
        self.rows[record.id] = record
        return record

    def get(self, entity_name: str, record_id: str) -> MemoryRecord | None:
        record = self.rows.get(record_id)
        if record is None or record.entity_name != entity_name:
            return None
        return record

    def update(
        self, entity_name: str, record_id: str, values: dict[str, Any]
    ) -> MemoryRecord:
        record = self.get(entity_name, record_id)
        if record is None:
            raise LookupError(f"no '{entity_name}' record {record_id} in this test run")
        record.data = {**record.data, **values}
        return record

    def seed(self, entity_name: str, data: dict[str, Any]) -> MemoryRecord:
        """Pre-load a record, so a test can start from an existing row."""
        return self.create(entity_name, data)

    def snapshot(self) -> list[dict[str, Any]]:
        """Every record the test run touched, for showing the user the result."""
        return [
            {"id": r.id, "entity": r.entity_name, "data": r.data} for r in self.rows.values()
        ]
