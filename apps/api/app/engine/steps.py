"""What each step type actually does.

One handler per step type, each taking the run environment and returning a
`StepOutcome`. Handlers never decide where the run goes next beyond their own
branch choice — the executor owns the flow — and they never commit, so a run
that fails part-way rolls back as one unit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import select

from app.engine import expressions
from app.models import AppUser, Notification, OutboundEmail, StepStatus
from app.runtime.fields import coerce_record
from app.specs.catalog import (
    BINARY_OPERATORS,
    Operator,
    StepType,
)
from app.specs.schema import AppSpec, Step


class StepFailure(Exception):
    """This step could not complete. The run stops and records why."""


@dataclass
class StepOutcome:
    status: StepStatus = StepStatus.OK
    #: Shown in the run log under the step.
    message: str | None = None
    #: Inputs and results, for the log's detail view.
    detail: dict[str, Any] = field(default_factory=dict)
    #: Merged into `context["steps"][step.id]`.
    outputs: dict[str, Any] = field(default_factory=dict)
    #: Merged into `context["vars"]`.
    variables: dict[str, Any] = field(default_factory=dict)
    #: Set by condition/approval steps to pick a branch.
    branch: str | None = None
    #: True when the run should stop here and wait for a person.
    waiting: bool = False


class Classifier(Protocol):
    """Sorts text into one of `categories`. Injected so a test run and an
    offline environment can both supply their own."""

    def __call__(self, text: str, categories: list[str]) -> str: ...


class RecordSink(Protocol):
    """The subset of `RecordStore` the engine needs.

    A test run passes a memory-backed implementation, which is why the engine
    never touches `RecordStore` concretely.
    """

    def create(
        self, entity_name: str, data: dict[str, Any], *, created_by: str | None = None
    ) -> Any: ...

    def update(self, entity_name: str, record_id: str, values: dict[str, Any]) -> Any: ...

    def get(self, entity_name: str, record_id: str) -> Any: ...


@dataclass
class RunEnv:
    """Everything a step needs, and nothing it does not."""

    spec: AppSpec
    project_id: str
    records: RecordSink
    session: Any = None  # SQLAlchemy Session; None for a test run
    classifier: Classifier | None = None
    is_test: bool = False
    #: In a test run, what the approver decides. True approves everything.
    test_approves: bool = True
    #: Collected instead of delivered during a test run.
    captured_notifications: list[dict[str, Any]] = field(default_factory=list)
    captured_emails: list[dict[str, Any]] = field(default_factory=list)

    def resolve(self, value: Any, context: dict[str, Any]) -> Any:
        try:
            return expressions.evaluate(value, context)
        except expressions.ExpressionError as exc:
            raise StepFailure(str(exc)) from exc


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def compare(left: Any, operator: Operator, right: Any) -> bool:
    """Evaluate one condition.

    Numeric comparisons coerce both sides, so `"7" > 5` behaves the way a
    non-technical user expects a form value to behave.
    """
    if operator is Operator.IS_EMPTY:
        return left is None or left == "" or left == []
    if operator is Operator.IS_NOT_EMPTY:
        return not (left is None or left == "" or left == [])

    if operator is Operator.CONTAINS:
        if left is None:
            return False
        if isinstance(left, (list, tuple)):
            return right in left
        return str(right).lower() in str(left).lower()

    left_number, right_number = _as_number(left), _as_number(right)
    both_numeric = left_number is not None and right_number is not None

    match operator:
        case Operator.EQ:
            if both_numeric:
                return left_number == right_number
            return str(left).strip().lower() == str(right).strip().lower()
        case Operator.NEQ:
            if both_numeric:
                return left_number != right_number
            return str(left).strip().lower() != str(right).strip().lower()
        case Operator.GT | Operator.GTE | Operator.LT | Operator.LTE:
            if not both_numeric:
                # Dates are ISO strings, so lexical order is chronological.
                left_number, right_number = str(left), str(right)
            match operator:
                case Operator.GT:
                    return left_number > right_number
                case Operator.GTE:
                    return left_number >= right_number
                case Operator.LT:
                    return left_number < right_number
                case _:
                    return left_number <= right_number

    raise StepFailure(f"unsupported operator '{operator}'")


def describe_comparison(left: Any, operator: Operator, right: Any, result: bool) -> str:
    """The condition in words, for the run log."""
    words = {
        Operator.EQ: "is",
        Operator.NEQ: "is not",
        Operator.GT: "is more than",
        Operator.GTE: "is at least",
        Operator.LT: "is less than",
        Operator.LTE: "is at most",
        Operator.CONTAINS: "contains",
        Operator.IS_EMPTY: "is empty",
        Operator.IS_NOT_EMPTY: "is not empty",
    }
    phrase = words.get(operator, str(operator))
    if operator in BINARY_OPERATORS:
        sentence = f"{left!r} {phrase} {right!r}"
    else:
        sentence = f"{left!r} {phrase}"
    return f"{sentence} — {'yes' if result else 'no'}"


# --------------------------------------------------------------------------
# Recipients
# --------------------------------------------------------------------------


def _describe_recipient(env: RunEnv, target: str, context: dict[str, Any]) -> str:
    """Who a notification is for, in words.

    A test log that says `{{ trigger.user.id }}` tells the reader nothing, and
    the test log is the thing that has to convince them the app works.
    """
    if not expressions.is_expression(target):
        role = env.spec.role(target)
        return f"the {role.label.lower()}" if role else target

    if "trigger.user" in target:
        name = context.get("trigger", {}).get("user", {}).get("name")
        return name or "the person who submitted it"

    try:
        return str(expressions.evaluate(target, context))
    except expressions.ExpressionError:
        return "the person it concerns"


def resolve_recipients(env: RunEnv, target: str, context: dict[str, Any]) -> list[AppUser]:
    """Who a notification goes to.

    `target` is either a role name — meaning everyone holding that role — or
    an expression resolving to one app user's id.
    """
    if env.session is None:
        return []

    if not expressions.is_expression(target):
        return list(
            env.session.scalars(
                select(AppUser).where(
                    AppUser.project_id == env.project_id,
                    AppUser.role == target,
                    AppUser.is_active.is_(True),
                )
            )
        )

    resolved = env.resolve(target, context)
    if not resolved:
        return []

    user = env.session.scalars(
        select(AppUser).where(
            AppUser.project_id == env.project_id, AppUser.id == str(resolved)
        )
    ).first()
    return [user] if user else []


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------


def _handle_create_record(env: RunEnv, step, context: dict[str, Any]) -> StepOutcome:
    entity = env.spec.entity(step.entity)
    if entity is None:
        raise StepFailure(f"entity '{step.entity}' is not in this app")

    resolved = env.resolve(step.values, context)
    coerced = coerce_record(entity, resolved, require_required=False)
    if not coerced.ok:
        raise StepFailure("; ".join(coerced.errors.values()))

    record = env.records.create(step.entity, coerced.data)
    return StepOutcome(
        message=f"Created a {entity.label.lower()}",
        detail={"entity": step.entity, "values": coerced.data, "record_id": record.id},
        outputs={"record_id": record.id},
    )


def _handle_update_record(env: RunEnv, step, context: dict[str, Any]) -> StepOutcome:
    entity = env.spec.entity(step.entity)
    if entity is None:
        raise StepFailure(f"entity '{step.entity}' is not in this app")

    record_id = env.resolve(step.record_id, context)
    if not record_id:
        raise StepFailure(f"'{step.record_id}' did not resolve to a record")

    resolved = env.resolve(step.values, context)
    coerced = coerce_record(
        entity, resolved, require_required=False, apply_defaults=False
    )
    if not coerced.ok:
        raise StepFailure("; ".join(coerced.errors.values()))

    try:
        env.records.update(step.entity, str(record_id), coerced.data)
    except LookupError as exc:
        raise StepFailure(str(exc)) from exc

    changes = ", ".join(f"{key} = {value}" for key, value in coerced.data.items())
    return StepOutcome(
        message=f"Set {changes}" if changes else "Nothing to change",
        detail={"entity": step.entity, "record_id": record_id, "values": coerced.data},
        outputs={"record_id": str(record_id)},
    )


def _handle_condition(env: RunEnv, step, context: dict[str, Any]) -> StepOutcome:
    left = env.resolve(step.left, context)
    right = env.resolve(step.right, context) if step.right is not None else None
    result = compare(left, step.operator, right)

    return StepOutcome(
        message=describe_comparison(left, step.operator, right, result),
        detail={
            "left": left,
            "operator": str(step.operator),
            "right": right,
            "result": result,
        },
        outputs={"result": result},
        branch=step.if_true if result else step.if_false,
    )


def _handle_notify_in_app(env: RunEnv, step, context: dict[str, Any]) -> StepOutcome:
    title = env.resolve(step.title, context)
    body = env.resolve(step.body, context)

    if env.is_test:
        who = _describe_recipient(env, step.to, context)
        env.captured_notifications.append({"to": who, "title": title, "body": body})
        return StepOutcome(
            message=f"Would notify {who}: {title}",
            detail={"to": who, "title": title, "body": body, "simulated": True},
        )

    recipients = resolve_recipients(env, step.to, context)
    if not recipients:
        # Not a failure: a role with nobody in it yet is a normal early state,
        # and stopping the run over it would be worse than carrying on.
        return StepOutcome(
            status=StepStatus.SKIPPED,
            message=f"Nobody to notify for '{step.to}'",
            detail={"to": step.to, "title": title},
        )

    for user in recipients:
        env.session.add(
            Notification(
                project_id=env.project_id,
                app_user_id=user.id,
                title=str(title)[:160],
                body=str(body),
                run_id=context.get("run_id"),
            )
        )

    names = ", ".join(user.name for user in recipients[:3])
    if len(recipients) > 3:
        names += f" and {len(recipients) - 3} more"
    return StepOutcome(
        message=f"Notified {names}",
        detail={"to": step.to, "title": title, "recipients": [u.id for u in recipients]},
    )


def _handle_notify_email(env: RunEnv, step, context: dict[str, Any]) -> StepOutcome:
    subject = env.resolve(step.subject, context)
    body = env.resolve(step.body, context)

    # `to` may be a role, an app user's id, or a plain address typed into a form.
    if expressions.is_expression(step.to):
        resolved = env.resolve(step.to, context)
        addresses = [str(resolved)] if resolved and "@" in str(resolved) else []
        if not addresses and resolved:
            addresses = [u.email for u in resolve_recipients(env, step.to, context)]
    else:
        addresses = [u.email for u in resolve_recipients(env, step.to, context)]

    if env.is_test:
        who = addresses or [_describe_recipient(env, step.to, context)]
        env.captured_emails.append({"to": who, "subject": subject, "body": body})
        return StepOutcome(
            message=f"Would email {', '.join(who)}: {subject}",
            detail={"to": who, "subject": subject, "body": body, "simulated": True},
        )

    if not addresses:
        return StepOutcome(
            status=StepStatus.SKIPPED,
            message=f"No email address for '{step.to}'",
            detail={"to": step.to, "subject": subject},
        )

    for address in addresses:
        env.session.add(
            OutboundEmail(
                project_id=env.project_id,
                to_email=address[:255],
                subject=str(subject)[:200],
                body=str(body),
                run_id=context.get("run_id"),
            )
        )

    return StepOutcome(
        message=f"Queued an email to {', '.join(addresses)}",
        detail={"to": addresses, "subject": subject},
    )


def _handle_ai_classify(env: RunEnv, step, context: dict[str, Any]) -> StepOutcome:
    text = str(env.resolve(step.input, context) or "").strip()
    if not text:
        # Fall back to the last category rather than fail: an empty complaint
        # is still a complaint, and it should reach a human.
        chosen = step.categories[-1]
        return StepOutcome(
            status=StepStatus.SKIPPED,
            message=f"Nothing to read, defaulted to '{chosen}'",
            detail={"categories": step.categories, "chosen": chosen},
            variables={step.output: chosen},
        )

    if env.classifier is None:
        raise StepFailure("no classifier is configured for this run")

    chosen = env.classifier(text, list(step.categories))
    if chosen not in step.categories:
        raise StepFailure(
            f"classifier returned '{chosen}', which is not one of "
            f"{', '.join(step.categories)}"
        )

    return StepOutcome(
        message=f"Read it as '{chosen}'",
        detail={
            "input": text[:300],
            "categories": step.categories,
            "chosen": chosen,
        },
        outputs={"chosen": chosen},
        variables={step.output: chosen},
    )


#: Approval is handled by the executor, since it owns pausing and resuming.
HANDLERS = {
    StepType.CREATE_RECORD: _handle_create_record,
    StepType.UPDATE_RECORD: _handle_update_record,
    StepType.CONDITION: _handle_condition,
    StepType.NOTIFY_IN_APP: _handle_notify_in_app,
    StepType.NOTIFY_EMAIL: _handle_notify_email,
    StepType.AI_CLASSIFY: _handle_ai_classify,
}


def run_step(env: RunEnv, step: Step, context: dict[str, Any]) -> StepOutcome:
    handler = HANDLERS.get(step.type)
    if handler is None:
        raise StepFailure(f"no handler for step type '{step.type}'")
    return handler(env, step, context)
