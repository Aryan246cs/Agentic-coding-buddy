"""The workflow executor.

A run is a cursor plus a context, both stored in the database. That is what
makes an approval that sits for three days cost nothing: the run is not a
thread waiting, it is a row. When the decision arrives, `resume_run` picks the
cursor back up and carries on.

The context is the run's whole memory:

    {
      "run_id":  "...",
      "trigger": {"entity": ..., "record_id": ..., "data": {...}, "user": {...}},
      "steps":   {"<step_id>": {...outputs...}},
      "vars":    {"priority": "Urgent"}
    }
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.steps import RunEnv, StepFailure, StepOutcome, run_step
from app.models import (
    Approval,
    ApprovalDecision,
    RunStatus,
    StepStatus,
    WorkflowRun,
    WorkflowRunStep,
    utcnow,
)
from app.specs.catalog import MAX_WORKFLOW_STEPS, StepType
from app.specs.schema import AppSpec, WorkflowSpec

logger = logging.getLogger(__name__)

#: Hard backstop against a cycle the validator somehow let through. A run may
#: visit more steps than the workflow has, because branches revisit none but
#: the budget must still allow every step plus headroom.
STEP_BUDGET = MAX_WORKFLOW_STEPS * 2


class WorkflowError(Exception):
    """The run could not be started or resumed at all."""


@dataclass
class RunResult:
    run: WorkflowRun
    #: Step log entries created by this call, oldest first.
    steps: list[WorkflowRunStep]
    env: RunEnv

    @property
    def status(self) -> str:
        return self.run.status

    @property
    def is_waiting(self) -> bool:
        return self.run.status == RunStatus.WAITING_APPROVAL


# --------------------------------------------------------------------------
# Starting
# --------------------------------------------------------------------------


def build_trigger_context(
    *,
    entity_name: str,
    record_id: str | None,
    data: dict[str, Any],
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "trigger": {
            "entity": entity_name,
            "record_id": record_id,
            "data": dict(data),
            "user": user or {"id": None, "email": "", "name": "Someone", "role": ""},
        },
        "steps": {},
        "vars": {},
    }


def _next_sequence(session: Session, project_id: str) -> int:
    highest = session.scalar(
        select(func.max(WorkflowRun.sequence)).where(WorkflowRun.project_id == project_id)
    )
    return (highest or 0) + 1


def start_run(
    env: RunEnv,
    workflow: WorkflowSpec,
    trigger_context: dict[str, Any],
    *,
    session: Session,
) -> RunResult:
    """Create a run and drive it until it finishes or hits an approval."""
    run = WorkflowRun(
        project_id=env.project_id,
        workflow_key=workflow.key,
        sequence=_next_sequence(session, env.project_id),
        status=RunStatus.RUNNING,
        context=trigger_context,
        cursor=workflow.steps[0].id,
        is_test=env.is_test,
        workflow_snapshot=workflow.model_dump(mode="json"),
    )
    session.add(run)
    session.flush()

    # Steps read `run_id` out of the context to stamp what they create.
    run.context = {**run.context, "run_id": run.id}

    return _drive(env, run, workflow, session=session)


# --------------------------------------------------------------------------
# Resuming
# --------------------------------------------------------------------------


def resume_run(
    env: RunEnv,
    run: WorkflowRun,
    *,
    approved: bool,
    session: Session,
    decided_by: str | None = None,
    note: str | None = None,
) -> RunResult:
    """Carry on a run that was waiting on a person."""
    if run.status != RunStatus.WAITING_APPROVAL:
        raise WorkflowError(f"run #{run.sequence} is not waiting for a decision")
    if run.cursor is None:
        raise WorkflowError(f"run #{run.sequence} has nowhere to resume from")

    workflow = _workflow_for(env, run)
    step = workflow.step(run.cursor)
    if step is None or step.type is not StepType.APPROVAL:
        raise WorkflowError(
            f"run #{run.sequence} is parked on '{run.cursor}', which is not an approval"
        )

    approval = session.scalars(
        select(Approval).where(
            Approval.run_id == run.id,
            Approval.step_id == step.id,
            Approval.decision == ApprovalDecision.PENDING,
        )
    ).first()

    if approval is not None:
        approval.decision = (
            ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED
        )
        approval.decided_by = decided_by
        approval.decided_at = utcnow()
        approval.note = note

    decision_word = "Approved" if approved else "Rejected"
    _log_step(
        session,
        run,
        step,
        StepOutcome(
            status=StepStatus.OK,
            message=f"{decision_word}{f' — {note}' if note else ''}",
            detail={
                "decision": decision_word.lower(),
                "role": step.role,
                "decided_by": decided_by,
                "note": note,
            },
            outputs={"decision": decision_word.lower(), "approved": approved},
        ),
        replace_waiting=True,
    )

    _merge_outputs(run, step.id, {"decision": decision_word.lower(), "approved": approved})

    onward = (step.on_approve if approved else step.on_reject) or workflow.default_next(step)
    run.cursor = onward
    run.status = RunStatus.RUNNING

    return _drive(env, run, workflow, session=session)


def _workflow_for(env: RunEnv, run: WorkflowRun) -> WorkflowSpec:
    """The workflow this run started against.

    A paused run finishes under the rules it began with, so editing a workflow
    never changes the outcome of something already in flight.
    """
    if run.workflow_snapshot:
        return WorkflowSpec.model_validate(run.workflow_snapshot)

    workflow = env.spec.workflow(run.workflow_key)
    if workflow is None:
        raise WorkflowError(f"workflow '{run.workflow_key}' is no longer in this app")
    return workflow


# --------------------------------------------------------------------------
# The loop
# --------------------------------------------------------------------------


def _drive(
    env: RunEnv, run: WorkflowRun, workflow: WorkflowSpec, *, session: Session
) -> RunResult:
    logged: list[WorkflowRunStep] = []
    budget = STEP_BUDGET

    while run.cursor is not None:
        budget -= 1
        if budget <= 0:
            return _fail(
                session,
                run,
                run.cursor,
                f"stopped after {STEP_BUDGET} steps — the workflow appears to loop",
                logged,
                env,
            )

        step = workflow.step(run.cursor)
        if step is None:
            return _fail(
                session, run, run.cursor, f"step '{run.cursor}' is not in this workflow",
                logged, env,
            )

        if step.type is StepType.APPROVAL:
            outcome = _handle_approval(env, run, step, session=session)
            # Logged either way: a real run shows "waiting for the manager",
            # a test run shows the decision it made on their behalf.
            logged.append(_log_step(session, run, step, outcome))
            if outcome.waiting:
                run.status = RunStatus.WAITING_APPROVAL
                session.flush()
                return RunResult(run=run, steps=logged, env=env)
        else:
            started = time.perf_counter()
            try:
                outcome = run_step(env, step, run.context)
            except StepFailure as exc:
                logged.append(
                    _log_step(
                        session,
                        run,
                        step,
                        StepOutcome(status=StepStatus.FAILED, message=str(exc)),
                        duration_ms=int((time.perf_counter() - started) * 1000),
                    )
                )
                return _fail(session, run, step.id, str(exc), logged, env)
            except Exception as exc:  # noqa: BLE001 - the run must record this
                logger.exception("step %s of run %s blew up", step.id, run.id)
                message = f"Something went wrong in this step: {exc}"
                logged.append(
                    _log_step(
                        session,
                        run,
                        step,
                        StepOutcome(status=StepStatus.FAILED, message=message),
                    )
                )
                return _fail(session, run, step.id, message, logged, env)

            outcome.detail.setdefault("duration_ms", int((time.perf_counter() - started) * 1000))
            logged.append(
                _log_step(
                    session, run, step, outcome,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            )

        if outcome.outputs:
            _merge_outputs(run, step.id, outcome.outputs)
        if outcome.variables:
            run.context = {
                **run.context,
                "vars": {**run.context.get("vars", {}), **outcome.variables},
            }

        run.cursor = outcome.branch or workflow.default_next(step)

    run.status = RunStatus.COMPLETED
    run.finished_at = utcnow()
    session.flush()
    return RunResult(run=run, steps=logged, env=env)


def _handle_approval(
    env: RunEnv, run: WorkflowRun, step, *, session: Session
) -> StepOutcome:
    """Park the run, or decide it outright when this is a test."""
    record_id = env.resolve(step.record_id, run.context)
    prompt = env.resolve(step.prompt, run.context)

    if env.is_test:
        approved = env.test_approves
        word = "approved" if approved else "rejected"
        return StepOutcome(
            message=f"Test {step.role} {word} it",
            detail={
                "role": step.role,
                "decision": word,
                "prompt": prompt,
                "simulated": True,
            },
            outputs={"decision": word, "approved": approved},
            branch=(step.on_approve if approved else step.on_reject),
        )

    session.add(
        Approval(
            project_id=env.project_id,
            run_id=run.id,
            step_id=step.id,
            role=step.role,
            entity_name=step.entity,
            record_id=str(record_id) if record_id else None,
            prompt=str(prompt)[:200],
        )
    )

    return StepOutcome(
        status=StepStatus.WAITING,
        message=f"Waiting for {step.role} to decide",
        detail={"role": step.role, "record_id": record_id, "prompt": prompt},
        waiting=True,
    )


# --------------------------------------------------------------------------
# Bookkeeping
# --------------------------------------------------------------------------


def _merge_outputs(run: WorkflowRun, step_id: str, outputs: dict[str, Any]) -> None:
    """Record a step's outputs so later steps can read them.

    The context dict is replaced rather than mutated, because SQLAlchemy does
    not notice in-place changes to a JSON column and the update would be lost.
    """
    steps = {**run.context.get("steps", {})}
    steps[step_id] = {**steps.get(step_id, {}), **outputs}
    run.context = {**run.context, "steps": steps}


def _log_step(
    session: Session,
    run: WorkflowRun,
    step,
    outcome: StepOutcome,
    *,
    duration_ms: int | None = None,
    replace_waiting: bool = False,
) -> WorkflowRunStep:
    """Append one line to the run log.

    `replace_waiting` turns the "waiting for manager" entry into the decision
    itself, so the log reads as one step rather than two.
    """
    if replace_waiting:
        existing = session.scalars(
            select(WorkflowRunStep).where(
                WorkflowRunStep.run_id == run.id,
                WorkflowRunStep.step_id == step.id,
                WorkflowRunStep.status == StepStatus.WAITING,
            )
        ).first()
        if existing is not None:
            existing.status = outcome.status
            existing.message = outcome.message
            existing.detail = outcome.detail
            waited = (utcnow() - existing.started_at).total_seconds()
            existing.duration_ms = int(waited * 1000)
            session.flush()
            return existing

    position = (
        session.scalar(
            select(func.count()).select_from(
                select(WorkflowRunStep.id)
                .where(WorkflowRunStep.run_id == run.id)
                .subquery()
            )
        )
        or 0
    )

    entry = WorkflowRunStep(
        run_id=run.id,
        position=position + 1,
        step_id=step.id,
        step_type=str(step.type),
        label=step.label[:160],
        status=outcome.status,
        detail=outcome.detail,
        message=outcome.message,
        duration_ms=duration_ms,
    )
    session.add(entry)
    session.flush()
    return entry


def _fail(
    session: Session,
    run: WorkflowRun,
    step_id: str | None,
    message: str,
    logged: list[WorkflowRunStep],
    env: RunEnv,
) -> RunResult:
    run.status = RunStatus.FAILED
    run.error = message
    run.failed_step = step_id
    run.finished_at = utcnow()
    session.flush()
    return RunResult(run=run, steps=logged, env=env)


# --------------------------------------------------------------------------
# Reading a run back
# --------------------------------------------------------------------------


def run_summary(run: WorkflowRun, steps: list[WorkflowRunStep] | None = None) -> dict[str, Any]:
    """A run shaped for the UI's run log."""
    entries = steps if steps is not None else list(run.steps)
    duration = None
    if run.finished_at:
        duration = round((run.finished_at - run.created_at).total_seconds(), 2)

    return {
        "id": run.id,
        "sequence": run.sequence,
        "workflow_key": run.workflow_key,
        "status": run.status,
        "is_test": run.is_test,
        "error": run.error,
        "failed_step": run.failed_step,
        "started_at": run.created_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "duration_seconds": duration,
        "steps": [
            {
                "position": entry.position,
                "step_id": entry.step_id,
                "step_type": entry.step_type,
                "label": entry.label,
                "status": entry.status,
                "message": entry.message,
                "detail": entry.detail,
                "duration_ms": entry.duration_ms,
            }
            for entry in entries
        ],
    }
