"""Describing a spec in plain English.

This is the screen where the product either earns trust or loses it. The user
has typed a sentence about how their office works and is about to find out
whether we understood. So none of this says "entity", "schema" or "workflow
node" — it says "what you'll store" and "what happens".

Everything here is derived from the spec, never from the model's prose, so the
plan the user approves is exactly the plan that gets built.
"""

from __future__ import annotations

import re
from typing import Any

from app.specs.catalog import (
    BINARY_OPERATORS,
    FieldType,
    Operator,
    RecordScope,
    ScreenType,
    StepType,
)
from app.specs.schema import AppSpec, Step, WorkflowSpec

FIELD_WORDS: dict[FieldType, str] = {
    FieldType.TEXT: "text",
    FieldType.LONG_TEXT: "a paragraph",
    FieldType.NUMBER: "a number",
    FieldType.DATE: "a date",
    FieldType.CHOICE: "a choice",
    FieldType.BOOLEAN: "yes or no",
    FieldType.REFERENCE: "a link to another record",
    FieldType.USER: "a person",
}

SCREEN_WORDS: dict[ScreenType, str] = {
    ScreenType.FORM: "a form to fill in",
    ScreenType.TABLE: "a list they can search",
    ScreenType.DETAIL: "one record in full",
    ScreenType.APPROVALS: "things waiting for them to approve",
}

OPERATOR_WORDS: dict[Operator, str] = {
    Operator.EQ: "is",
    Operator.NEQ: "is not",
    Operator.GT: "is more than",
    Operator.GTE: "is at least",
    Operator.LT: "is less than",
    Operator.LTE: "is at most",
    Operator.CONTAINS: "contains",
    Operator.IS_EMPTY: "is empty",
    Operator.IS_NOT_EMPTY: "is filled in",
}


def _plain(expression: Any) -> str:
    """Turn `{{ trigger.data.days }}` into 'the number of days'."""
    if not isinstance(expression, str):
        return str(expression)

    text = expression
    replacements = {
        "{{ trigger.user.name }}": "the person who submitted it",
        "{{ trigger.user.email }}": "their email address",
        "{{ trigger.user.id }}": "the person who submitted it",
        "{{ trigger.record_id }}": "the submitted record",
        "{{ now.date }}": "today's date",
    }
    for needle, phrase in replacements.items():
        text = text.replace(needle, phrase)

    # Anything left of the form {{ trigger.data.x }} or {{ vars.x }}.

    text = re.sub(r"\{\{\s*trigger\.data\.([a-z0-9_]+)\s*\}\}", r"\1", text)
    text = re.sub(r"\{\{\s*vars\.([a-z0-9_]+)\s*\}\}", r"the \1 it worked out", text)
    text = re.sub(r"\{\{\s*steps\.[a-z0-9_]+\.record_id\s*\}\}", "that record", text)
    text = re.sub(r"\{\{\s*[a-z0-9_.]+\s*\}\}", "a value", text)
    return text.replace("_", " ").strip()


def describe_step(spec: AppSpec, workflow: WorkflowSpec, step: Step) -> dict[str, Any]:
    """One step, as a line a shop owner could read."""
    entity_label = ""
    if hasattr(step, "entity"):
        entity = spec.entity(step.entity)
        entity_label = entity.label.lower() if entity else step.entity

    match step.type:
        case StepType.CREATE_RECORD:
            sentence = f"Create a new {entity_label}"
        case StepType.UPDATE_RECORD:
            changes = ", ".join(
                f"{key.replace('_', ' ')} to {_plain(value)}"
                for key, value in step.values.items()
            )
            sentence = f"Update the {entity_label}" + (f" — set {changes}" if changes else "")
        case StepType.CONDITION:
            phrase = OPERATOR_WORDS.get(step.operator, str(step.operator))
            left = _plain(step.left)
            if step.operator in BINARY_OPERATORS:
                sentence = f"Check whether {left} {phrase} {_plain(step.right)}"
            else:
                sentence = f"Check whether {left} {phrase}"
        case StepType.APPROVAL:
            role = spec.role(step.role)
            sentence = f"Wait for the {(role.label if role else step.role).lower()} to approve or reject it"
        case StepType.NOTIFY_IN_APP:
            sentence = f"Send {_who(spec, step.to)} a message in the app"
        case StepType.NOTIFY_EMAIL:
            sentence = f"Email {_who(spec, step.to)}"
        case StepType.AI_CLASSIFY:
            sentence = (
                f"Read it and decide if it is {_join_words(list(step.categories))}"
            )
        case _:
            sentence = step.label

    branches: list[dict[str, str]] = []
    if step.type is StepType.CONDITION:
        branches = [
            {"when": "yes", "goes_to": step.if_true or _next_label(workflow, step)},
            {"when": "no", "goes_to": step.if_false or _next_label(workflow, step)},
        ]
    elif step.type is StepType.APPROVAL:
        branches = [
            {"when": "approved", "goes_to": step.on_approve or _next_label(workflow, step)},
            {"when": "rejected", "goes_to": step.on_reject or _next_label(workflow, step)},
        ]

    return {
        "id": step.id,
        "type": str(step.type),
        "label": step.label,
        "sentence": sentence,
        "branches": branches,
    }


def _who(spec: AppSpec, target: str) -> str:
    """A notification's recipient, as a noun phrase that reads naturally."""
    role = spec.role(target)
    if role:
        return f"the {role.label.lower()}"
    return _plain(target)


def _next_label(workflow: WorkflowSpec, step: Step) -> str:
    return workflow.default_next(step) or "(finish)"


def _join_words(words: list[str]) -> str:
    if len(words) <= 1:
        return words[0] if words else ""
    return f"{', '.join(words[:-1])} or {words[-1]}"


def describe_workflow(spec: AppSpec, workflow: WorkflowSpec) -> dict[str, Any]:
    trigger_entity = spec.entity(workflow.trigger.entity)
    label = trigger_entity.label.lower() if trigger_entity else workflow.trigger.entity

    return {
        "key": workflow.key,
        "name": workflow.name,
        "description": workflow.description,
        "starts_when": f"Someone submits a {label}",
        "steps": [describe_step(spec, workflow, step) for step in workflow.steps],
    }


def describe_plan(spec: AppSpec) -> dict[str, Any]:
    """The whole plan, in the words the user will read before clicking Build."""
    people = []
    for role in spec.roles:
        screens = spec.screens_for_role(role.name)
        can_approve = any(
            step.type is StepType.APPROVAL and step.role == role.name
            for workflow in spec.workflows
            for step in workflow.steps
        )
        people.append(
            {
                "name": role.name,
                "label": role.label,
                "description": role.description,
                "is_admin": role.is_admin,
                "can_approve": can_approve,
                "sees": [screen.title for screen in screens],
            }
        )

    stores = []
    for entity in spec.entities:
        stores.append(
            {
                "name": entity.name,
                "label": entity.label_plural,
                "fields": [
                    {
                        "label": field_spec.label,
                        "kind": FIELD_WORDS.get(field_spec.type, str(field_spec.type)),
                        "required": field_spec.required,
                        "choices": list(field_spec.choices),
                    }
                    for field_spec in entity.fields
                ],
            }
        )

    pages = []
    for screen in spec.screens:
        roles = [spec.role(name) for name in screen.roles]
        who = [role.label for role in roles if role] or ["Admins only"]
        pages.append(
            {
                "key": screen.key,
                "title": screen.title,
                "kind": SCREEN_WORDS.get(screen.type, str(screen.type)),
                "who": who,
                "only_their_own": screen.record_scope is RecordScope.OWN,
            }
        )

    return {
        "name": spec.name,
        "description": spec.description,
        "people": people,
        "stores": stores,
        "pages": pages,
        "workflows": [describe_workflow(spec, workflow) for workflow in spec.workflows],
        "counts": {
            "roles": len(spec.roles),
            "entities": len(spec.entities),
            "screens": len(spec.screens),
            "workflows": len(spec.workflows),
            "steps": sum(len(w.steps) for w in spec.workflows),
        },
    }
