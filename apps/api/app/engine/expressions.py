"""The `{{ ... }}` expression language.

Deliberately tiny: a dotted path lookup into a run context, nothing more. No
arithmetic, no function calls, no `eval`. A spec comes from a language model,
so the only safe expression language is one that cannot express anything
dangerous.

    "{{ trigger.data.days }}"            -> the value, with its type intact
    "Leave for {{ trigger.data.days }}"  -> interpolated into a string
    5                                     -> a literal, passed through

Readable roots:
    trigger.data.<field>     the submitted form values
    trigger.record_id        the record the trigger created
    trigger.user.<id|email|name>
    steps.<step_id>.record_id
    steps.<step_id>.<key>    other outputs a step recorded
    vars.<name>              values written by ai_classify
    now.<date|datetime|time>
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

EXPR_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")

#: A string that is exactly one expression and nothing else.
WHOLE_EXPR_RE = re.compile(r"^\s*\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}\s*$")

VALID_ROOTS = frozenset({"trigger", "steps", "vars", "now"})

TRIGGER_KEYS = frozenset({"data", "record_id", "user", "entity"})
TRIGGER_USER_KEYS = frozenset({"id", "email", "name", "role"})
NOW_KEYS = frozenset({"date", "datetime", "time"})


class ExpressionError(ValueError):
    """A path could not be resolved at run time."""


def references(value: Any) -> list[str]:
    """Every expression path inside `value`, walking dicts and lists."""
    found: list[str] = []
    if isinstance(value, str):
        found.extend(EXPR_RE.findall(value))
    elif isinstance(value, dict):
        for item in value.values():
            found.extend(references(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(references(item))
    return found


def is_expression(value: Any) -> bool:
    return isinstance(value, str) and bool(EXPR_RE.search(value))


def validate_path(path: str) -> str | None:
    """Check a path's shape. Returns an error message, or None if it is fine.

    This is a static check, so it can only catch a malformed shape — whether
    `trigger.data.days` exists is a question for the validator, which knows
    the spec's fields.
    """
    parts = path.split(".")
    root = parts[0]

    if root not in VALID_ROOTS:
        return (
            f"unknown expression root '{root}' in '{{{{ {path} }}}}' "
            f"(expected one of: {', '.join(sorted(VALID_ROOTS))})"
        )

    match root:
        case "trigger":
            if len(parts) < 2 or parts[1] not in TRIGGER_KEYS:
                return (
                    f"'{{{{ {path} }}}}' must be one of "
                    f"trigger.{{{', '.join(sorted(TRIGGER_KEYS))}}}"
                )
            if parts[1] == "data" and len(parts) != 3:
                return f"'{{{{ {path} }}}}' must name a field, e.g. trigger.data.status"
            if parts[1] == "user":
                if len(parts) != 3 or parts[2] not in TRIGGER_USER_KEYS:
                    return (
                        f"'{{{{ {path} }}}}' must be trigger.user."
                        f"{{{', '.join(sorted(TRIGGER_USER_KEYS))}}}"
                    )
            if parts[1] in ("record_id", "entity") and len(parts) != 2:
                return f"'{{{{ {path} }}}}' takes no further keys"
        case "steps":
            if len(parts) != 3:
                return (
                    f"'{{{{ {path} }}}}' must be steps.<step_id>.<key>, "
                    "e.g. steps.create_request.record_id"
                )
        case "vars":
            if len(parts) != 2:
                return f"'{{{{ {path} }}}}' must be vars.<name>"
        case "now":
            if len(parts) != 2 or parts[1] not in NOW_KEYS:
                return f"'{{{{ {path} }}}}' must be now.{{{', '.join(sorted(NOW_KEYS))}}}"

    return None


def _now_value(key: str) -> str:
    moment = datetime.now(UTC)
    match key:
        case "date":
            return moment.date().isoformat()
        case "time":
            return moment.time().replace(microsecond=0).isoformat()
        case _:
            return moment.replace(microsecond=0).isoformat()


def resolve_path(path: str, context: dict[str, Any]) -> Any:
    """Look one path up in a run context. Raises `ExpressionError` if missing."""
    parts = path.split(".")

    if parts[0] == "now":
        return _now_value(parts[1] if len(parts) > 1 else "datetime")

    cursor: Any = context
    for index, part in enumerate(parts):
        if isinstance(cursor, dict):
            if part not in cursor:
                where = ".".join(parts[:index]) or "context"
                raise ExpressionError(
                    f"'{{{{ {path} }}}}' could not be resolved: "
                    f"'{part}' is not available on {where}"
                )
            cursor = cursor[part]
        else:
            raise ExpressionError(
                f"'{{{{ {path} }}}}' could not be resolved: "
                f"'{'.'.join(parts[:index])}' is not a structure"
            )
    return cursor


def evaluate(value: Any, context: dict[str, Any]) -> Any:
    """Resolve expressions in `value` against `context`.

    A string that is exactly one expression keeps the resolved value's type,
    so `"{{ trigger.data.days }}"` compares as a number. Anything else is
    interpolated into a string.
    """
    if isinstance(value, dict):
        return {key: evaluate(item, context) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [evaluate(item, context) for item in value]
    if not isinstance(value, str):
        return value

    whole = WHOLE_EXPR_RE.match(value)
    if whole:
        return resolve_path(whole.group(1), context)

    def replace(match: re.Match[str]) -> str:
        resolved = resolve_path(match.group(1), context)
        return "" if resolved is None else str(resolved)

    return EXPR_RE.sub(replace, value)
