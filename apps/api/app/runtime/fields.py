"""Turning submitted values into clean record data.

Every write to a generated app goes through `coerce_record` — form
submissions from a browser and `create_record` steps from a workflow alike.
The entity spec is the only authority on what a field may hold, so a field
that is not on the entity is dropped rather than stored.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.specs.catalog import FieldType
from app.specs.schema import EntitySpec, FieldSpec

MAX_TEXT = 500
MAX_LONG_TEXT = 5000


@dataclass
class CoercionResult:
    data: dict[str, Any] = field(default_factory=dict)
    #: field name -> what is wrong with it, phrased for the person filling it in.
    errors: dict[str, str] = field(default_factory=dict)
    #: Names that were submitted but are not on the entity.
    ignored: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _coerce_number(raw: Any) -> tuple[Any, str | None]:
    if isinstance(raw, bool):
        return None, "must be a number"
    if isinstance(raw, (int, float)):
        return raw, None
    text = str(raw).strip().replace(",", "")
    try:
        value = float(text)
    except ValueError:
        return None, "must be a number"
    return (int(value) if value.is_integer() else value), None


def _coerce_date(raw: Any) -> tuple[Any, str | None]:
    if isinstance(raw, datetime):
        return raw.date().isoformat(), None
    if isinstance(raw, date):
        return raw.isoformat(), None
    text = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat(), None
        except ValueError:
            continue
    # Last resort: an ISO datetime, which browsers sometimes send.
    try:
        return datetime.fromisoformat(text).date().isoformat(), None
    except ValueError:
        return None, "must be a date like 2026-03-14"


def _coerce_boolean(raw: Any) -> tuple[Any, str | None]:
    if isinstance(raw, bool):
        return raw, None
    text = str(raw).strip().lower()
    if text in ("true", "yes", "1", "on"):
        return True, None
    if text in ("false", "no", "0", "off", ""):
        return False, None
    return None, "must be yes or no"


def coerce_value(field_spec: FieldSpec, raw: Any) -> tuple[Any, str | None]:
    """One value, cleaned. Returns `(value, error)` — error is None on success."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, None

    match field_spec.type:
        case FieldType.TEXT:
            return str(raw).strip()[:MAX_TEXT], None
        case FieldType.LONG_TEXT:
            return str(raw).strip()[:MAX_LONG_TEXT], None
        case FieldType.NUMBER:
            return _coerce_number(raw)
        case FieldType.DATE:
            return _coerce_date(raw)
        case FieldType.BOOLEAN:
            return _coerce_boolean(raw)
        case FieldType.CHOICE:
            text = str(raw).strip()
            if text not in field_spec.choices:
                return None, f"must be one of: {', '.join(field_spec.choices)}"
            return text, None
        case FieldType.REFERENCE | FieldType.USER:
            return str(raw).strip()[:32], None

    return None, f"has an unsupported type '{field_spec.type}'"


def coerce_record(
    entity: EntitySpec,
    payload: dict[str, Any],
    *,
    allowed_fields: list[str] | None = None,
    require_required: bool = True,
    apply_defaults: bool = True,
) -> CoercionResult:
    """Clean a whole payload against an entity.

    `allowed_fields` narrows what may be written — a form screen passes its
    own field list so a crafted request cannot set `status` directly when the
    form never offered it.
    """
    result = CoercionResult()
    permitted = set(allowed_fields) if allowed_fields is not None else None

    known = {f.name for f in entity.fields}
    for key in payload:
        if key not in known:
            result.ignored.append(key)

    for field_spec in entity.fields:
        writable = permitted is None or field_spec.name in permitted

        if field_spec.name in payload and writable:
            value, error = coerce_value(field_spec, payload[field_spec.name])
            if error:
                result.errors[field_spec.name] = f"{field_spec.label} {error}"
                continue
        elif apply_defaults and field_spec.default is not None:
            value = field_spec.default
        else:
            value = None

        if value is None and field_spec.required and require_required and writable:
            result.errors[field_spec.name] = f"{field_spec.label} is required"
            continue

        if value is not None:
            result.data[field_spec.name] = value

    return result


def display_value(field_spec: FieldSpec, value: Any) -> str:
    """Render a stored value for a table cell or an email body."""
    if value is None or value == "":
        return "—"
    if field_spec.type is FieldType.BOOLEAN:
        return "Yes" if value else "No"
    return str(value)
