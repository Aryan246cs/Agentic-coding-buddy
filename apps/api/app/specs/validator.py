"""Spec validation.

Pydantic already guarantees the *shape* of a spec. This module checks that it
holds together: that a screen's entity exists, that a step's branch target is
a real step, that `{{ trigger.data.days }}` names a field that was actually
submitted. Those are the mistakes a language model makes, and they are the
ones that produce an app that renders but does not work.

Errors block a save. Warnings are shown to the user and to the planner but
never stand in the way of a build — a missing empty-state message is not a
reason to refuse someone their app.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from app.engine import expressions
from app.specs.catalog import (
    BINARY_OPERATORS,
    MAX_WORKFLOW_STEPS,
    NUMERIC_OPERATORS,
    RESERVED_FIELD_NAMES,
    FieldType,
    Operator,
    ScreenType,
    StepType,
)
from app.specs.schema import AppSpec, EntitySpec, WorkflowSpec


@dataclass(frozen=True)
class Issue:
    #: Dotted location in the spec, e.g. "workflows.leave_approval.steps.notify".
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class ValidationReport:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, path: str, message: str) -> None:
        self.errors.append(Issue(path, message))

    def warn(self, path: str, message: str) -> None:
        self.warnings.append(Issue(path, message))

    def as_prompt_feedback(self) -> str:
        """Errors phrased for feeding back to the planner on a retry."""
        return "\n".join(f"- {issue}" for issue in self.errors)

    def to_dict(self) -> dict[str, list[dict[str, str]]]:
        return {
            "errors": [{"path": i.path, "message": i.message} for i in self.errors],
            "warnings": [{"path": i.path, "message": i.message} for i in self.warnings],
        }


def _duplicates(names: list[str]) -> list[str]:
    return sorted(name for name, count in Counter(names).items() if count > 1)


def validate_app_spec(spec: AppSpec) -> ValidationReport:
    report = ValidationReport()

    _check_entities(spec, report)
    _check_roles(spec, report)
    _check_screens(spec, report)
    _check_workflows(spec, report)

    return report


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


def _check_entities(spec: AppSpec, report: ValidationReport) -> None:
    for name in _duplicates([e.name for e in spec.entities]):
        report.error("entities", f"two entities are both named '{name}'")

    entity_names = {e.name for e in spec.entities}

    for entity in spec.entities:
        base = f"entities.{entity.name}"

        for name in _duplicates([f.name for f in entity.fields]):
            report.error(base, f"two fields are both named '{name}'")

        if not any(f.is_title for f in entity.fields):
            report.warn(
                base,
                "no field is marked is_title, so tables will fall back to the "
                f"first field ('{entity.fields[0].name}')",
            )

        if sum(1 for f in entity.fields if f.is_title) > 1:
            report.warn(base, "more than one field is marked is_title; the first wins")

        for field_spec in entity.fields:
            where = f"{base}.{field_spec.name}"

            if field_spec.name in RESERVED_FIELD_NAMES:
                report.error(
                    where,
                    f"'{field_spec.name}' is added automatically and must not "
                    "be declared",
                )

            if field_spec.type is FieldType.CHOICE and not field_spec.choices:
                report.error(where, "a choice field must list its choices")
            if field_spec.type is not FieldType.CHOICE and field_spec.choices:
                report.error(
                    where, f"choices are only allowed on a choice field, not {field_spec.type}"
                )

            if field_spec.type is FieldType.REFERENCE:
                if not field_spec.references:
                    report.error(where, "a reference field must name the entity it points to")
                elif field_spec.references not in entity_names:
                    report.error(
                        where,
                        f"points at entity '{field_spec.references}', which does not exist",
                    )
            elif field_spec.references:
                report.error(
                    where,
                    f"'references' is only allowed on a reference field, not {field_spec.type}",
                )

            if (
                field_spec.type is FieldType.CHOICE
                and field_spec.default is not None
                and field_spec.default not in field_spec.choices
            ):
                report.error(
                    where,
                    f"default '{field_spec.default}' is not one of the choices "
                    f"({', '.join(field_spec.choices)})",
                )


def _check_roles(spec: AppSpec, report: ValidationReport) -> None:
    for name in _duplicates([r.name for r in spec.roles]):
        report.error("roles", f"two roles are both named '{name}'")

    admins = [r.name for r in spec.roles if r.is_admin]
    if not admins:
        report.error(
            "roles",
            "no role is marked is_admin — the app owner would not be able to "
            "see anything",
        )
    elif len(admins) > 1:
        report.warn("roles", f"more than one admin role ({', '.join(admins)})")


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------


def _check_screens(spec: AppSpec, report: ValidationReport) -> None:
    for key in _duplicates([s.key for s in spec.screens]):
        report.error("screens", f"two screens are both keyed '{key}'")

    role_names = {r.name for r in spec.roles}
    reachable_roles: set[str] = set()

    for screen in spec.screens:
        base = f"screens.{screen.key}"
        entity = spec.entity(screen.entity)

        if entity is None:
            report.error(base, f"uses entity '{screen.entity}', which does not exist")
            continue

        for role_name in screen.roles:
            if role_name not in role_names:
                report.error(base, f"is granted to role '{role_name}', which does not exist")
            else:
                reachable_roles.add(role_name)

        if not screen.roles:
            report.warn(base, "no role is granted this screen, so only admins will see it")

        field_names = {f.name for f in entity.fields}
        for field_name in screen.fields:
            if field_name not in field_names:
                report.error(
                    base,
                    f"shows field '{field_name}', which is not on entity "
                    f"'{entity.name}'",
                )

        for filter_field, filter_value in screen.filters.items():
            target = entity.field(filter_field)
            if target is None:
                report.error(
                    base, f"filters on '{filter_field}', which is not on '{entity.name}'"
                )
            elif target.type is FieldType.CHOICE and filter_value not in target.choices:
                report.error(
                    base,
                    f"filters {filter_field} = '{filter_value}', which is not one "
                    f"of its choices ({', '.join(target.choices)})",
                )

        _check_screen_type_rules(spec, screen, entity, report)

    for role in spec.roles:
        if not role.is_admin and role.name not in reachable_roles:
            report.warn(
                f"roles.{role.name}",
                "has no screens, so this role can log in but see nothing",
            )


def _check_screen_type_rules(
    spec: AppSpec, screen, entity: EntitySpec, report: ValidationReport
) -> None:
    base = f"screens.{screen.key}"

    if screen.type is ScreenType.FORM:
        if screen.filters:
            report.error(base, "a form screen cannot have filters")
        if screen.submit_workflow:
            workflow = spec.workflow(screen.submit_workflow)
            if workflow is None:
                report.error(
                    base,
                    f"submits to workflow '{screen.submit_workflow}', which does not exist",
                )
            elif workflow.trigger.entity != screen.entity:
                report.error(
                    base,
                    f"submits to workflow '{workflow.key}', but that workflow is "
                    f"triggered by '{workflow.trigger.entity}', not '{screen.entity}'",
                )
        else:
            report.warn(
                base,
                "submitting this form saves a record but starts no workflow, so "
                "nobody is notified",
            )

        shown = set(screen.fields) if screen.fields else {f.name for f in entity.fields}
        for field_spec in entity.fields:
            if field_spec.required and field_spec.name not in shown:
                report.error(
                    base,
                    f"'{field_spec.name}' is required on '{entity.name}' but is not "
                    "on this form, so submitting it can never succeed",
                )
    else:
        if screen.submit_workflow:
            report.error(base, f"submit_workflow is only valid on a form, not a {screen.type}")

    if screen.type is ScreenType.APPROVALS and not any(
        w.trigger.entity == screen.entity
        and any(s.type is StepType.APPROVAL for s in w.steps)
        for w in spec.workflows
    ):
        report.warn(
            base,
            f"is an approvals queue for '{entity.name}', but no workflow on that "
            "entity has an approval step, so it will always be empty",
        )


# --------------------------------------------------------------------------
# Workflows
# --------------------------------------------------------------------------


def _check_workflows(spec: AppSpec, report: ValidationReport) -> None:
    for key in _duplicates([w.key for w in spec.workflows]):
        report.error("workflows", f"two workflows are both keyed '{key}'")

    for workflow in spec.workflows:
        _check_workflow(spec, workflow, report)


def _check_workflow(spec: AppSpec, workflow: WorkflowSpec, report: ValidationReport) -> None:
    base = f"workflows.{workflow.key}"

    trigger_entity = spec.entity(workflow.trigger.entity)
    if trigger_entity is None:
        report.error(
            base,
            f"is triggered by entity '{workflow.trigger.entity}', which does not exist",
        )

    if len(workflow.steps) > MAX_WORKFLOW_STEPS:
        report.error(
            base,
            f"has {len(workflow.steps)} steps, above the limit of {MAX_WORKFLOW_STEPS}",
        )

    for step_id in _duplicates([s.id for s in workflow.steps]):
        report.error(base, f"two steps are both keyed '{step_id}'")

    step_ids = {s.id for s in workflow.steps}
    role_names = {r.name for r in spec.roles}

    # Values written by ai_classify, readable later as {{ vars.x }}.
    declared_vars = {s.output for s in workflow.steps if s.type is StepType.AI_CLASSIFY}

    for step in workflow.steps:
        where = f"{base}.steps.{step.id}"

        def check_target(target: str | None, label: str) -> None:
            if target is None:
                return
            if target not in step_ids:
                report.error(where, f"{label} points at step '{target}', which does not exist")
            elif target == step.id:
                report.error(where, f"{label} points at itself, which would never finish")

        check_target(step.next, "next")

        match step.type:
            case StepType.CREATE_RECORD:
                _check_entity_values(spec, step.entity, step.values, where, report)
            case StepType.UPDATE_RECORD:
                _check_entity_values(spec, step.entity, step.values, where, report)
                if not expressions.is_expression(step.record_id):
                    report.error(
                        where,
                        "record_id must be an expression such as "
                        "'{{ trigger.record_id }}'",
                    )
            case StepType.CONDITION:
                check_target(step.if_true, "if_true")
                check_target(step.if_false, "if_false")
                if step.operator in BINARY_OPERATORS and step.right is None:
                    report.error(where, f"operator '{step.operator}' needs a right value")
                if step.operator not in BINARY_OPERATORS and step.right is not None:
                    report.warn(
                        where, f"operator '{step.operator}' ignores the right value"
                    )
                if step.if_true is None and step.if_false is None:
                    report.warn(
                        where,
                        "neither branch names a target, so both outcomes continue "
                        "to the next step and the condition has no effect",
                    )
                _check_numeric_comparison(spec, workflow, step, where, report)
            case StepType.APPROVAL:
                check_target(step.on_approve, "on_approve")
                check_target(step.on_reject, "on_reject")
                if step.role not in role_names:
                    report.error(
                        where, f"waits on role '{step.role}', which does not exist"
                    )
                elif spec.role(step.role) and not spec.screens_for_role(step.role):
                    report.warn(
                        where,
                        f"waits on role '{step.role}', which has no screens to "
                        "approve from",
                    )
                if spec.entity(step.entity) is None:
                    report.error(
                        where, f"approves entity '{step.entity}', which does not exist"
                    )
            case StepType.NOTIFY_IN_APP | StepType.NOTIFY_EMAIL:
                if not expressions.is_expression(step.to) and step.to not in role_names:
                    report.error(
                        where,
                        f"notifies '{step.to}', which is neither a role nor an "
                        "expression",
                    )
            case StepType.AI_CLASSIFY:
                if len(set(step.categories)) != len(step.categories):
                    report.error(where, "categories contain a duplicate")

        _check_expressions(spec, workflow, step, declared_vars, where, report)

    _check_reachability(workflow, report, base)
    _check_no_cycles(workflow, report, base)


def _check_no_cycles(workflow: WorkflowSpec, report: ValidationReport, base: str) -> None:
    """Refuse a flow that can loop back on itself.

    There is no delay or wait primitive, so a cycle is an infinite loop. The
    executor has a step budget as a backstop, but a spec that would hit it
    should never be saved in the first place.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {step.id: WHITE for step in workflow.steps}

    def visit(step_id: str, trail: list[str]) -> None:
        colour[step_id] = GREY
        step = workflow.step(step_id)
        if step is not None:
            for target in sorted(workflow.successors(step)):
                if target not in colour:
                    continue  # broken target, already reported
                if colour[target] == GREY:
                    loop = " -> ".join([*trail, step_id, target])
                    report.error(base, f"steps loop forever: {loop}")
                elif colour[target] == WHITE:
                    visit(target, [*trail, step_id])
        colour[step_id] = BLACK

    for step in workflow.steps:
        if colour[step.id] == WHITE:
            visit(step.id, [])


def _check_reachability(workflow: WorkflowSpec, report: ValidationReport, base: str) -> None:
    """Walk the flow from the first step and flag anything never reached.

    A step the runtime can never arrive at is almost always a planner mistake
    — usually a branch that forgot to point somewhere — and it would otherwise
    sit in the spec looking like it works.
    """
    reached = {workflow.steps[0].id}
    frontier = [workflow.steps[0]]

    while frontier:
        step = frontier.pop()
        for target in workflow.successors(step):
            if target in reached:
                continue
            next_step = workflow.step(target)
            if next_step is None:
                continue  # already reported as a broken target
            reached.add(target)
            frontier.append(next_step)

    for step in workflow.steps:
        if step.id not in reached:
            report.warn(
                f"{base}.steps.{step.id}",
                "is unreachable: no path from the first step arrives here",
            )


def _check_entity_values(
    spec: AppSpec,
    entity_name: str,
    values: dict[str, object],
    where: str,
    report: ValidationReport,
) -> None:
    entity = spec.entity(entity_name)
    if entity is None:
        report.error(where, f"writes to entity '{entity_name}', which does not exist")
        return

    for field_name, value in values.items():
        target = entity.field(field_name)
        if target is None:
            report.error(
                where, f"writes field '{field_name}', which is not on '{entity_name}'"
            )
            continue
        if (
            target.type is FieldType.CHOICE
            and isinstance(value, str)
            and not expressions.is_expression(value)
            and value not in target.choices
        ):
            report.error(
                where,
                f"writes {field_name} = '{value}', which is not one of its choices "
                f"({', '.join(target.choices)})",
            )


def _check_numeric_comparison(
    spec: AppSpec, workflow: WorkflowSpec, step, where: str, report: ValidationReport
) -> None:
    """Warn when `>` or `<` is used against a field that holds text."""
    if step.operator not in NUMERIC_OPERATORS:
        return

    entity = spec.entity(workflow.trigger.entity)
    if entity is None or not isinstance(step.left, str):
        return

    for path in expressions.references(step.left):
        parts = path.split(".")
        if parts[:2] == ["trigger", "data"] and len(parts) == 3:
            target = entity.field(parts[2])
            if target and target.type not in (FieldType.NUMBER, FieldType.DATE):
                report.warn(
                    where,
                    f"compares '{parts[2]}' with '{step.operator}', but that field "
                    f"holds {target.type}, not a number",
                )


def _check_expressions(
    spec: AppSpec,
    workflow: WorkflowSpec,
    step,
    declared_vars: set[str],
    where: str,
    report: ValidationReport,
) -> None:
    """Every `{{ path }}` in a step must resolve to something real."""
    trigger_entity = spec.entity(workflow.trigger.entity)
    step_ids = {s.id for s in workflow.steps}
    payload = step.model_dump(exclude={"id", "label", "type"})

    for path in expressions.references(payload):
        shape_error = expressions.validate_path(path)
        if shape_error:
            report.error(where, shape_error)
            continue

        parts = path.split(".")
        match parts:
            case ["trigger", "data", field_name]:
                if trigger_entity and trigger_entity.field(field_name) is None:
                    report.error(
                        where,
                        f"reads '{{{{ {path} }}}}', but '{field_name}' is not a field "
                        f"on '{workflow.trigger.entity}'",
                    )
            case ["steps", step_id, _]:
                if step_id not in step_ids:
                    report.error(
                        where,
                        f"reads '{{{{ {path} }}}}', but there is no step '{step_id}'",
                    )
                elif step_id == step.id:
                    report.error(where, f"reads its own output via '{{{{ {path} }}}}'")
            case ["vars", var_name]:
                if var_name not in declared_vars:
                    report.error(
                        where,
                        f"reads '{{{{ {path} }}}}', but no ai_classify step writes "
                        f"'{var_name}'",
                    )
