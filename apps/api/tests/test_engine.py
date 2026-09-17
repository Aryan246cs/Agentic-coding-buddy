"""Workflow engine tests.

This is the one place where tests are worth the budget: the engine is where a
silent bug means a customer's approval quietly never happens. The three demo
workflows are the real proof — if one runtime runs all three, the design holds.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.engine.executor import (
    build_trigger_context,
    resume_run,
    run_summary,
    start_run,
)
from app.engine.steps import RunEnv, compare
from app.models import (
    Approval,
    ApprovalDecision,
    Notification,
    OutboundEmail,
    RunStatus,
    StepStatus,
)
from app.runtime.memory_store import MemoryRecordStore
from app.runtime.records import RecordStore
from app.specs.catalog import Operator
from tests.conftest import step_log, stub_classifier


def make_env(session, project, spec, users=None, **overrides) -> RunEnv:
    return RunEnv(
        spec=spec,
        project_id=project.id,
        records=RecordStore(session, project.id, spec),
        session=session,
        **overrides,
    )


def submit(store, spec, entity_name: str, data: dict, user):
    """Create the record a form submission would create, then its context."""
    record = store.create(entity_name, data, created_by=user.id)
    return record, build_trigger_context(
        entity_name=entity_name,
        record_id=record.id,
        data=data,
        user={"id": user.id, "email": user.email, "name": user.name, "role": user.role},
    )


# --------------------------------------------------------------------------
# Leave management — approval, pause, resume
# --------------------------------------------------------------------------


def test_leave_request_pauses_for_the_manager(session, app_factory, demo_specs):
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)
    store = env.records

    record, context = submit(
        store, spec, "leave_requests",
        {"leave_type": "Casual", "start_date": "2026-04-01", "days": 3, "status": "Pending"},
        users["employee"],
    )

    result = start_run(env, spec.workflow("leave_approval"), context, session=session)

    assert result.status == RunStatus.WAITING_APPROVAL
    assert result.run.cursor == "manager_decision"
    assert step_log(result) == [
        ("notify_manager", StepStatus.OK),
        ("manager_decision", StepStatus.WAITING),
    ]

    # The manager was told, and an approval is now pending on their role.
    notifications = session.scalars(select(Notification)).all()
    assert len(notifications) == 1
    assert notifications[0].app_user_id == users["manager"].id
    assert "3 day(s) of Casual" in notifications[0].body

    approval = session.scalars(select(Approval)).one()
    assert approval.decision == ApprovalDecision.PENDING
    assert approval.role == "manager"
    assert approval.record_id == record.id

    # Nothing has been decided, so the record is untouched.
    assert store.require("leave_requests", record.id).data["status"] == "Pending"


def test_approving_finishes_the_run_and_updates_the_record(session, app_factory, demo_specs):
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)
    store = env.records

    record, context = submit(
        store, spec, "leave_requests",
        {"leave_type": "Sick", "start_date": "2026-05-02", "days": 2, "status": "Pending"},
        users["employee"],
    )
    paused = start_run(env, spec.workflow("leave_approval"), context, session=session)

    resumed = resume_run(
        make_env(session, project, spec),
        paused.run,
        approved=True,
        session=session,
        decided_by=users["manager"].id,
        note="Get well soon",
    )

    assert resumed.status == RunStatus.COMPLETED
    assert store.require("leave_requests", record.id).data["status"] == "Approved"

    approval = session.scalars(select(Approval)).one()
    assert approval.decision == ApprovalDecision.APPROVED
    assert approval.decided_by == users["manager"].id
    assert approval.note == "Get well soon"

    # The employee was notified, and the rejection branch never ran.
    log = run_summary(resumed.run)
    visited = [s["step_id"] for s in log["steps"]]
    assert visited == [
        "notify_manager",
        "manager_decision",
        "mark_approved",
        "notify_employee",
    ]
    assert "mark_rejected" not in visited

    employee_notes = session.scalars(
        select(Notification).where(Notification.app_user_id == users["employee"].id)
    ).all()
    assert len(employee_notes) == 1


def test_rejecting_takes_the_other_branch(session, app_factory, demo_specs):
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)
    store = env.records

    record, context = submit(
        store, spec, "leave_requests",
        {"leave_type": "Unpaid", "start_date": "2026-06-01", "days": 10, "status": "Pending"},
        users["employee"],
    )
    paused = start_run(env, spec.workflow("leave_approval"), context, session=session)

    resumed = resume_run(
        make_env(session, project, spec), paused.run, approved=False, session=session
    )

    assert resumed.status == RunStatus.COMPLETED
    assert store.require("leave_requests", record.id).data["status"] == "Rejected"

    visited = [s["step_id"] for s in run_summary(resumed.run)["steps"]]
    assert "mark_rejected" in visited
    assert "mark_approved" not in visited


def test_a_decision_cannot_be_applied_twice(session, app_factory, demo_specs):
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)

    _, context = submit(
        env.records, spec, "leave_requests",
        {"leave_type": "Casual", "start_date": "2026-04-01", "days": 1, "status": "Pending"},
        users["employee"],
    )
    paused = start_run(env, spec.workflow("leave_approval"), context, session=session)
    resume_run(make_env(session, project, spec), paused.run, approved=True, session=session)

    from app.engine.executor import WorkflowError

    with pytest.raises(WorkflowError, match="not waiting"):
        resume_run(
            make_env(session, project, spec), paused.run, approved=False, session=session
        )


# --------------------------------------------------------------------------
# Expenses — numeric conditions and three approval levels
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("amount", "expected_path", "expected_approver"),
    [
        (2500, ["check_small", "auto_approve", "notify_employee"], "Auto"),
        (
            25000,
            ["check_small", "check_medium", "manager_approval"],
            None,  # pauses for the manager
        ),
        (
            90000,
            ["check_small", "check_medium", "director_approval"],
            None,  # pauses for the director
        ),
    ],
)
def test_expense_routes_by_amount(
    session, app_factory, demo_specs, amount, expected_path, expected_approver
):
    spec = demo_specs["expense_approval"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)

    record, context = submit(
        env.records, spec, "expenses",
        {
            "title": "Client dinner",
            "amount": amount,
            "category": "Food",
            "spent_on": "2026-03-01",
            "status": "Pending",
        },
        users["employee"],
    )

    result = start_run(env, spec.workflow("expense_approval"), context, session=session)

    assert [s.step_id for s in result.steps] == expected_path

    if expected_approver:
        assert result.status == RunStatus.COMPLETED
        stored = env.records.require("expenses", record.id).data
        assert stored["status"] == "Approved"
        assert stored["approved_by"] == expected_approver
    else:
        assert result.status == RunStatus.WAITING_APPROVAL


def test_large_expense_needs_the_director_and_records_who_approved(
    session, app_factory, demo_specs
):
    spec = demo_specs["expense_approval"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)

    record, context = submit(
        env.records, spec, "expenses",
        {
            "title": "New laptops",
            "amount": 120000,
            "category": "Equipment",
            "spent_on": "2026-03-02",
            "status": "Pending",
        },
        users["employee"],
    )
    paused = start_run(env, spec.workflow("expense_approval"), context, session=session)

    approval = session.scalars(select(Approval)).one()
    assert approval.role == "director"

    resumed = resume_run(
        make_env(session, project, spec),
        paused.run,
        approved=True,
        session=session,
        decided_by=users["director"].id,
    )

    assert resumed.status == RunStatus.COMPLETED
    stored = env.records.require("expenses", record.id).data
    assert stored["status"] == "Approved"
    assert stored["approved_by"] == "Director"


def test_amount_submitted_as_text_still_compares_numerically(
    session, app_factory, demo_specs
):
    """A browser sends form values as strings; routing must not care."""
    spec = demo_specs["expense_approval"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)

    _, context = submit(
        env.records, spec, "expenses",
        {
            "title": "Taxi",
            "amount": "800",
            "category": "Travel",
            "spent_on": "2026-03-03",
            "status": "Pending",
        },
        users["employee"],
    )
    result = start_run(env, spec.workflow("expense_approval"), context, session=session)

    assert result.status == RunStatus.COMPLETED
    assert [s.step_id for s in result.steps] == [
        "check_small",
        "auto_approve",
        "notify_employee",
    ]


# --------------------------------------------------------------------------
# Complaints — AI classification, branching, email
# --------------------------------------------------------------------------


def test_urgent_complaint_escalates_and_emails_the_customer(
    session, app_factory, demo_specs
):
    spec = demo_specs["customer_complaints"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec, classifier=stub_classifier("Urgent"))

    record, context = submit(
        env.records, spec, "complaints",
        {
            "subject": "Order never arrived",
            "details": "I paid three weeks ago and nothing has come.",
            "customer_email": "buyer@example.com",
            "status": "New",
        },
        users["customer"],
    )

    result = start_run(env, spec.workflow("complaint_triage"), context, session=session)

    assert result.status == RunStatus.COMPLETED
    assert [s.step_id for s in result.steps] == [
        "classify",
        "save_priority",
        "is_urgent",
        "escalate",
        "notify_manager",
        "acknowledge_customer",
    ]

    stored = env.records.require("complaints", record.id).data
    assert stored["priority"] == "Urgent"
    assert stored["status"] == "Escalated"

    email = session.scalars(select(OutboundEmail)).one()
    assert email.to_email == "buyer@example.com"
    assert "Order never arrived" in email.body
    assert email.sent_at is None  # queued, not sent inline


def test_normal_complaint_goes_to_support_and_skips_escalation(
    session, app_factory, demo_specs
):
    spec = demo_specs["customer_complaints"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec, classifier=stub_classifier("Normal"))

    record, context = submit(
        env.records, spec, "complaints",
        {
            "subject": "Wrong colour",
            "details": "I ordered blue and got green.",
            "customer_email": "buyer2@example.com",
            "status": "New",
        },
        users["customer"],
    )

    result = start_run(env, spec.workflow("complaint_triage"), context, session=session)

    assert result.status == RunStatus.COMPLETED
    visited = [s.step_id for s in result.steps]
    assert visited == [
        "classify",
        "save_priority",
        "is_urgent",
        "assign_support",
        "notify_support",
        "acknowledge_customer",
    ]
    assert "escalate" not in visited
    assert "notify_manager" not in visited

    # Both branches converge on the acknowledgement, so every customer hears
    # back regardless of how their complaint was graded.
    email = session.scalars(select(OutboundEmail)).one()
    assert email.to_email == "buyer2@example.com"

    stored = env.records.require("complaints", record.id).data
    assert stored["status"] == "Assigned"
    assert stored["priority"] == "Normal"


def test_a_classifier_answering_off_menu_fails_the_run_loudly(
    session, app_factory, demo_specs
):
    spec = demo_specs["customer_complaints"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec, classifier=stub_classifier("Catastrophic"))

    _, context = submit(
        env.records, spec, "complaints",
        {
            "subject": "Broken",
            "details": "It broke.",
            "customer_email": "b@example.com",
            "status": "New",
        },
        users["customer"],
    )

    result = start_run(env, spec.workflow("complaint_triage"), context, session=session)

    assert result.status == RunStatus.FAILED
    assert result.run.failed_step == "classify"
    assert "Catastrophic" in result.run.error


# --------------------------------------------------------------------------
# Test runs
# --------------------------------------------------------------------------


def test_a_test_run_writes_nothing_and_sends_nothing(session, app_factory, demo_specs):
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)

    memory = MemoryRecordStore(project_id=project.id)
    record = memory.create(
        "leave_requests",
        {"leave_type": "Casual", "start_date": "2026-04-01", "days": 4, "status": "Pending"},
    )
    env = RunEnv(
        spec=spec,
        project_id=project.id,
        records=memory,
        session=session,
        is_test=True,
        test_approves=True,
    )
    context = build_trigger_context(
        entity_name="leave_requests",
        record_id=record.id,
        data={"leave_type": "Casual", "start_date": "2026-04-01", "days": 4},
        user={"id": users["employee"].id, "email": "e@x.com", "name": "Asha", "role": "employee"},
    )

    result = start_run(env, spec.workflow("leave_approval"), context, session=session)

    # It ran all the way through without pausing on the approval.
    assert result.status == RunStatus.COMPLETED
    assert [s.step_id for s in result.steps] == [
        "notify_manager",
        "manager_decision",
        "mark_approved",
        "notify_employee",
    ]
    assert memory.rows[record.id].data["status"] == "Approved"

    # And nothing real was created.
    assert session.scalars(select(Notification)).all() == []
    assert session.scalars(select(OutboundEmail)).all() == []
    assert session.scalars(select(Approval)).all() == []
    assert len(env.captured_notifications) == 2


def test_a_test_run_can_reject_instead(session, app_factory, demo_specs):
    spec = demo_specs["leave_management"]
    project, _ = app_factory.build(spec)

    memory = MemoryRecordStore(project_id=project.id)
    record = memory.create("leave_requests", {"leave_type": "Sick", "days": 1, "status": "Pending"})
    env = RunEnv(
        spec=spec,
        project_id=project.id,
        records=memory,
        session=session,
        is_test=True,
        test_approves=False,
    )
    context = build_trigger_context(
        entity_name="leave_requests",
        record_id=record.id,
        data={"leave_type": "Sick", "days": 1, "start_date": "2026-04-01"},
    )

    result = start_run(env, spec.workflow("leave_approval"), context, session=session)

    assert result.status == RunStatus.COMPLETED
    assert memory.rows[record.id].data["status"] == "Rejected"


# --------------------------------------------------------------------------
# Failure handling
# --------------------------------------------------------------------------


def test_a_missing_record_fails_the_run_with_a_readable_reason(
    session, app_factory, demo_specs
):
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)

    context = build_trigger_context(
        entity_name="leave_requests",
        record_id="does-not-exist",
        data={"leave_type": "Casual", "days": 2, "start_date": "2026-04-01"},
        user={"id": users["employee"].id, "email": "e@x.com", "name": "E", "role": "employee"},
    )
    paused = start_run(env, spec.workflow("leave_approval"), context, session=session)
    resumed = resume_run(
        make_env(session, project, spec), paused.run, approved=True, session=session
    )

    assert resumed.status == RunStatus.FAILED
    assert resumed.run.failed_step == "mark_approved"
    assert "does-not-exist" in resumed.run.error


def test_notifying_a_role_with_nobody_in_it_is_skipped_not_fatal(
    session, app_factory, demo_specs
):
    """An app whose roles are not staffed yet must still work."""
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)

    # Remove the manager, leaving the role empty.
    session.delete(users["manager"])
    session.flush()

    env = make_env(session, project, spec)
    _, context = submit(
        env.records, spec, "leave_requests",
        {"leave_type": "Casual", "start_date": "2026-04-01", "days": 2, "status": "Pending"},
        users["employee"],
    )

    result = start_run(env, spec.workflow("leave_approval"), context, session=session)

    assert [s.status for s in result.steps] == [StepStatus.SKIPPED, StepStatus.WAITING]
    assert result.status == RunStatus.WAITING_APPROVAL


def test_run_sequence_numbers_are_per_project(session, app_factory, demo_specs):
    spec = demo_specs["leave_management"]
    first, users_a = app_factory.build(spec, slug="app-a")
    second, users_b = app_factory.build(spec, slug="app-b")

    for project, users in ((first, users_a), (second, users_b), (first, users_a)):
        env = make_env(session, project, spec)
        _, context = submit(
            env.records, spec, "leave_requests",
            {"leave_type": "Casual", "start_date": "2026-04-01", "days": 1, "status": "Pending"},
            users["employee"],
        )
        start_run(env, spec.workflow("leave_approval"), context, session=session)

    from app.models import WorkflowRun

    a_runs = session.scalars(
        select(WorkflowRun).where(WorkflowRun.project_id == first.id)
    ).all()
    b_runs = session.scalars(
        select(WorkflowRun).where(WorkflowRun.project_id == second.id)
    ).all()

    assert sorted(r.sequence for r in a_runs) == [1, 2]
    assert sorted(r.sequence for r in b_runs) == [1]


def test_an_edit_mid_run_does_not_change_a_paused_run(session, app_factory, demo_specs):
    """A run finishes under the rules it started with."""
    spec = demo_specs["leave_management"]
    project, users = app_factory.build(spec)
    env = make_env(session, project, spec)

    record, context = submit(
        env.records, spec, "leave_requests",
        {"leave_type": "Casual", "start_date": "2026-04-01", "days": 3, "status": "Pending"},
        users["employee"],
    )
    paused = start_run(env, spec.workflow("leave_approval"), context, session=session)

    # The owner edits the workflow while the approval is pending: approving now
    # would mark the request "Rejected" under the new rules.
    edited = spec.model_copy(deep=True)
    approved_step = edited.workflow("leave_approval").step("mark_approved")
    approved_step.values = {"status": "Rejected"}

    resumed = resume_run(
        make_env(session, project, edited), paused.run, approved=True, session=session
    )

    assert resumed.status == RunStatus.COMPLETED
    # The snapshot won: the in-flight run used the original rules.
    assert env.records.require("leave_requests", record.id).data["status"] == "Approved"


# --------------------------------------------------------------------------
# Comparison rules
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("left", "operator", "right", "expected"),
    [
        (5000, Operator.LT, 5000, False),
        (4999, Operator.LT, 5000, True),
        ("4999", Operator.LT, 5000, True),
        (50000, Operator.LTE, 50000, True),
        ("Urgent", Operator.EQ, "Urgent", True),
        ("urgent", Operator.EQ, "Urgent", True),
        ("Urgent", Operator.NEQ, "Normal", True),
        ("2026-05-01", Operator.GT, "2026-04-30", True),
        ("hello world", Operator.CONTAINS, "WORLD", True),
        (None, Operator.IS_EMPTY, None, True),
        ("", Operator.IS_EMPTY, None, True),
        ("x", Operator.IS_NOT_EMPTY, None, True),
        (None, Operator.CONTAINS, "x", False),
        (True, Operator.EQ, "true", True),
    ],
)
def test_compare(left, operator, right, expected):
    assert compare(left, operator, right) is expected
