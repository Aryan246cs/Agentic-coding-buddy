"""Spec schemas — the contract between the AI planner, the runtime and the UI.

An AppSpec is the whole of a generated application: what it stores, who uses
it, what they see, and what happens when they act. The runtime renders and
executes it; it never runs generated code.

Two rules hold this together:
  1. Every type used here comes from `catalog.py`.
  2. Every cross-reference (a screen naming an entity, a step naming a role)
     is checked by `validator.py` before a spec is ever saved.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.specs.catalog import (
    FieldType,
    Operator,
    RecordScope,
    ScreenType,
    StepType,
    TriggerType,
)

# A machine name: snake_case, starts with a letter. Used for entities, fields,
# roles, screens, steps and workflows so every reference is unambiguous.
Name = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,48}$", strip_whitespace=True),
]
Label = Annotated[str, StringConstraints(min_length=1, max_length=80, strip_whitespace=True)]

SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{1,38}[a-z0-9])?$")


class SpecModel(BaseModel):
    """Base for every spec node: unknown keys are an error, not a shrug.

    A planner that invents a property must fail loudly rather than have it
    silently dropped and produce an app that quietly misbehaves.
    """

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------


class FieldSpec(SpecModel):
    name: Name
    label: Label
    type: FieldType
    required: bool = False
    help_text: str | None = Field(default=None, max_length=200)

    #: Allowed values, required when `type` is `choice`.
    choices: list[Label] = Field(default_factory=list, max_length=20)

    #: Target entity name, required when `type` is `reference`.
    references: Name | None = None

    #: Shown in tables and used as the record's headline in detail views.
    #: At least one field per entity should set this.
    is_title: bool = False

    default: str | float | bool | None = None


class EntitySpec(SpecModel):
    """A thing the app stores. Becomes rows in the shared `records` table."""

    name: Name
    label: Label
    label_plural: Label
    fields: list[FieldSpec] = Field(min_length=1, max_length=25)

    def field(self, name: str) -> FieldSpec | None:
        return next((f for f in self.fields if f.name == name), None)

    @property
    def title_field(self) -> FieldSpec:
        """The field used as a record's headline, falling back to the first."""
        return next((f for f in self.fields if f.is_title), self.fields[0])


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------


class RoleSpec(SpecModel):
    name: Name
    label: Label
    description: str | None = Field(default=None, max_length=200)

    #: An admin bypasses `record_scope` and sees every screen. Exactly one role
    #: in a spec should be an admin — the person who owns the app.
    is_admin: bool = False


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------


class ScreenSpec(SpecModel):
    key: Name
    title: Label
    type: ScreenType
    entity: Name

    #: Roles that may open this screen. Empty means "no role but admins".
    roles: list[Name] = Field(default_factory=list)

    #: Entity fields to show, in order. Empty means every field.
    fields: list[Name] = Field(default_factory=list, max_length=25)

    #: Whether a non-admin sees only their own records or all of them.
    record_scope: RecordScope = RecordScope.OWN

    #: FORM only — the workflow to start when the form is submitted.
    submit_workflow: Name | None = None

    #: TABLE and APPROVALS only — fixed filter, e.g. {"status": "pending"}.
    filters: dict[Name, str] = Field(default_factory=dict)

    #: Shown when the screen has no records yet.
    empty_text: str | None = Field(default=None, max_length=160)

    icon: str | None = Field(default=None, max_length=32)


# --------------------------------------------------------------------------
# Workflow steps
#
# Steps are an ordered list, not a free graph. Flow falls through to the next
# step unless a branching step names a target. That is expressive enough for
# approvals and conditions, and far easier to validate and to generate
# reliably than arbitrary nodes and edges.
# --------------------------------------------------------------------------


class StepBase(SpecModel):
    id: Name
    #: Shown in the run log. Written for the person reading it, not the dev.
    label: Label

    #: Where to go after this step. None means the next step in the list, and
    #: falling off the end of the list finishes the run. An explicit `next` is
    #: how a branch skips the steps that belong to the other branch.
    next: Name | None = None


class CreateRecordStep(StepBase):
    type: Literal[StepType.CREATE_RECORD] = StepType.CREATE_RECORD
    entity: Name
    #: field name -> literal or `{{ expression }}`.
    values: dict[Name, Any] = Field(default_factory=dict)


class UpdateRecordStep(StepBase):
    type: Literal[StepType.UPDATE_RECORD] = StepType.UPDATE_RECORD
    entity: Name
    #: Expression resolving to a record id, e.g. `{{ trigger.record_id }}`.
    record_id: str
    values: dict[Name, Any] = Field(default_factory=dict)


class ConditionStep(StepBase):
    type: Literal[StepType.CONDITION] = StepType.CONDITION
    left: Any
    operator: Operator
    right: Any = None
    #: Step ids. None means "fall through to the next step".
    if_true: Name | None = None
    if_false: Name | None = None


class ApprovalStep(StepBase):
    """Pauses the run until someone in `role` decides.

    The run is persisted and picked up again when the decision arrives, so an
    approval can sit for days without holding anything open.
    """

    type: Literal[StepType.APPROVAL] = StepType.APPROVAL
    role: Name
    entity: Name
    record_id: str
    #: Shown to the approver above the Approve / Reject buttons.
    prompt: Label
    on_approve: Name | None = None
    on_reject: Name | None = None


class NotifyInAppStep(StepBase):
    type: Literal[StepType.NOTIFY_IN_APP] = StepType.NOTIFY_IN_APP
    #: A role name, or an expression resolving to an app_user id.
    to: str
    title: Label
    body: str = Field(max_length=500)


class NotifyEmailStep(StepBase):
    type: Literal[StepType.NOTIFY_EMAIL] = StepType.NOTIFY_EMAIL
    to: str
    subject: Label
    body: str = Field(max_length=2000)


class AiClassifyStep(StepBase):
    """Sorts text into one of `categories`. The only AI call inside a run."""

    type: Literal[StepType.AI_CLASSIFY] = StepType.AI_CLASSIFY
    #: Expression resolving to the text to classify.
    input: str
    categories: list[Label] = Field(min_length=2, max_length=10)
    #: Name to store the result under, readable as `{{ vars.<output> }}`.
    output: Name


Step = Annotated[
    CreateRecordStep
    | UpdateRecordStep
    | ConditionStep
    | ApprovalStep
    | NotifyInAppStep
    | NotifyEmailStep
    | AiClassifyStep,
    Field(discriminator="type"),
]


class TriggerSpec(SpecModel):
    type: TriggerType = TriggerType.FORM_SUBMISSION
    #: Entity whose form submission starts this workflow.
    entity: Name


class WorkflowSpec(SpecModel):
    key: Name
    name: Label
    description: str | None = Field(default=None, max_length=300)
    trigger: TriggerSpec
    steps: list[Step] = Field(min_length=1)

    def step(self, step_id: str) -> Step | None:
        return next((s for s in self.steps if s.id == step_id), None)

    def fallthrough(self, step_id: str) -> str | None:
        """The step that follows `step_id` in list order, if any."""
        for index, step in enumerate(self.steps):
            if step.id == step_id:
                remaining = self.steps[index + 1 :]
                return remaining[0].id if remaining else None
        return None

    def default_next(self, step: Step) -> str | None:
        """Where a non-branching step goes: its `next`, else the following step."""
        return step.next or self.fallthrough(step.id)

    def successors(self, step: Step) -> set[str]:
        """Every step that could run after `step`.

        The validator uses this to find unreachable steps and the executor
        uses it to move; sharing one definition keeps them honest.
        """
        onward = self.default_next(step)

        if isinstance(step, ConditionStep):
            targets = {step.if_true or onward, step.if_false or onward}
        elif isinstance(step, ApprovalStep):
            targets = {step.on_approve or onward, step.on_reject or onward}
        else:
            targets = {onward}

        return {target for target in targets if target is not None}


# --------------------------------------------------------------------------
# The whole application
# --------------------------------------------------------------------------


class AppSpec(SpecModel):
    spec_version: Literal[1] = 1
    name: Label
    description: str = Field(max_length=500)
    entities: list[EntitySpec] = Field(min_length=1, max_length=8)
    roles: list[RoleSpec] = Field(min_length=1, max_length=6)
    screens: list[ScreenSpec] = Field(min_length=1, max_length=20)
    workflows: list[WorkflowSpec] = Field(default_factory=list, max_length=6)

    def entity(self, name: str) -> EntitySpec | None:
        return next((e for e in self.entities if e.name == name), None)

    def role(self, name: str) -> RoleSpec | None:
        return next((r for r in self.roles if r.name == name), None)

    def screen(self, key: str) -> ScreenSpec | None:
        return next((s for s in self.screens if s.key == key), None)

    def workflow(self, key: str) -> WorkflowSpec | None:
        return next((w for w in self.workflows if w.key == key), None)

    def screens_for_role(self, role_name: str) -> list[ScreenSpec]:
        role = self.role(role_name)
        if role and role.is_admin:
            return list(self.screens)
        return [s for s in self.screens if role_name in s.roles]

    @property
    def admin_role(self) -> RoleSpec:
        return next((r for r in self.roles if r.is_admin), self.roles[0])


# --------------------------------------------------------------------------
# Websites — the other product. Deliberately much simpler: a site has no
# data, no users and no workflows, so it is content plus a template choice.
# --------------------------------------------------------------------------


class SiteSection(SpecModel):
    key: Name
    heading: Label
    body: str = Field(default="", max_length=1500)
    #: Short bullets, e.g. services offered or skills.
    items: list[Label] = Field(default_factory=list, max_length=12)
    image_query: str | None = Field(default=None, max_length=80)


class SiteSpec(SpecModel):
    spec_version: Literal[1] = 1
    template: Name
    #: Theme key from the template's palette set.
    theme: Name = "slate"
    site_name: Label
    tagline: Label
    hero_body: str = Field(default="", max_length=600)
    hero_image_query: str | None = Field(default=None, max_length=80)
    sections: list[SiteSection] = Field(default_factory=list, max_length=8)
    contact_email: str | None = None
    contact_phone: str | None = Field(default=None, max_length=32)
    location: str | None = Field(default=None, max_length=120)
    links: dict[Name, str] = Field(default_factory=dict)
    cta_label: Label | None = None
