"""Loading the built-in templates.

The demo specs are not just examples — they are the one-click templates users
start from, and the fixtures the tests run against. Keeping them as JSON on
disk means they go through exactly the same parsing and validation as anything
a planner produces.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.specs.schema import AppSpec
from app.specs.validator import validate_app_spec

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "demos"

#: How each template is introduced in the UI, in the user's language.
TEMPLATE_BLURBS: dict[str, str] = {
    "leave_management": "Staff request time off. Their manager approves it.",
    "expense_approval": "Staff claim expenses. Small ones clear themselves; "
    "bigger ones need a manager or a director.",
    "customer_complaints": "Customers raise problems. Urgent ones reach a "
    "manager, the rest go to your support team.",
}


class TemplateNotFound(LookupError):
    pass


@lru_cache
def load_template(name: str) -> AppSpec:
    """One template, parsed and checked.

    A broken built-in template is a bug in the product, not bad user input, so
    it raises rather than returning something half-valid.
    """
    path = TEMPLATE_DIR / f"{name}.json"
    if not path.is_file():
        raise TemplateNotFound(f"no template named '{name}'")

    spec = AppSpec.model_validate(json.loads(path.read_text()))

    report = validate_app_spec(spec)
    if not report.ok:
        raise ValueError(
            f"built-in template '{name}' is invalid:\n{report.as_prompt_feedback()}"
        )

    return spec


def template_names() -> list[str]:
    return sorted(path.stem for path in TEMPLATE_DIR.glob("*.json"))


def list_templates() -> list[dict[str, object]]:
    """Templates shaped for the picker on the dashboard."""
    cards = []
    for name in template_names():
        spec = load_template(name)
        cards.append(
            {
                "key": name,
                "name": spec.name,
                "blurb": TEMPLATE_BLURBS.get(name, spec.description),
                "roles": [role.label for role in spec.roles],
                "screen_count": len(spec.screens),
                "workflow_count": len(spec.workflows),
            }
        )
    return cards
