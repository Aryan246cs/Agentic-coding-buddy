"""Turning plain English into a validated spec.

The loop is: ask, validate, and if it failed, hand the errors back and ask
once more. Two attempts, then give up honestly — a third rarely helps and the
user is waiting.

Nothing invalid is ever returned. A caller either gets a spec that passed the
validator or an exception explaining what could not be fixed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.ai import prompts
from app.ai.provider import AIError, AIProvider, EchoProvider, get_provider
from app.specs.schema import AppSpec, SiteSpec
from app.specs.validator import ValidationReport, validate_app_spec

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2


class PlanningError(AIError):
    """A usable spec could not be produced."""

    def __init__(self, message: str, report: ValidationReport | None = None):
        super().__init__(message)
        self.report = report


@dataclass
class PlanResult:
    spec: AppSpec
    report: ValidationReport
    attempts: int = 1
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_micros: int = 0
    #: True when the offline planner answered, so the UI can say so.
    offline: bool = False


@dataclass
class SitePlanResult:
    spec: SiteSpec
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_micros: int = 0
    offline: bool = False


# --------------------------------------------------------------------------
# Apps
# --------------------------------------------------------------------------


def plan_app(description: str, provider: AIProvider | None = None) -> PlanResult:
    """Build an app spec from a description."""
    description = description.strip()
    if len(description) < 15:
        raise PlanningError(
            "Please describe your process in a sentence or two — who submits "
            "something, and who acts on it."
        )

    provider = provider or get_provider()

    if isinstance(provider, EchoProvider):
        return _offline_plan(description)

    prompt = f"Build a configuration for this:\n\n{description}"
    return _attempt(
        provider,
        system=prompts.APP_PLANNER_SYSTEM,
        prompt=prompt,
        source_description=description,
    )


def revise_app(
    spec: AppSpec, instruction: str, provider: AIProvider | None = None
) -> PlanResult:
    """Apply a plain-English change to an existing spec."""
    instruction = instruction.strip()
    if len(instruction) < 4:
        raise PlanningError("Please say what you would like to change.")

    provider = provider or get_provider()
    if isinstance(provider, EchoProvider):
        raise PlanningError(
            "Editing with words needs an AI key. Set ANTHROPIC_API_KEY or "
            "GROQ_API_KEY, or edit the app directly."
        )

    current = spec.model_dump_json(indent=None, exclude_defaults=True)
    prompt = (
        f"Current configuration:\n{current}\n\n"
        f"Instruction:\n{instruction}\n\n"
        "Return the complete updated configuration."
    )
    return _attempt(provider, system=prompts.REVISE_SYSTEM, prompt=prompt)


def _attempt(
    provider: AIProvider,
    *,
    system: str,
    prompt: str,
    source_description: str | None = None,
) -> PlanResult:
    """Ask, validate, and retry once with the errors in hand."""
    schema = _app_schema()
    messages = prompt
    totals = {"input": 0, "output": 0, "cost": 0}
    last_report: ValidationReport | None = None
    last_problem = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        completion = provider.complete(
            system=system, prompt=messages, schema=schema, max_tokens=12000
        )
        totals["input"] += completion.input_tokens
        totals["output"] += completion.output_tokens
        totals["cost"] += completion.cost_micros

        try:
            payload = completion.json()
        except AIError as exc:
            last_problem = str(exc)
            messages = f"{prompt}\n\n{prompts.repair_prompt(str(exc))}"
            continue

        try:
            spec = AppSpec.model_validate(payload)
        except ValidationError as exc:
            last_problem = _readable_pydantic_errors(exc)
            logger.info("planner attempt %s failed schema: %s", attempt, last_problem)
            messages = f"{prompt}\n\n{prompts.repair_prompt(last_problem)}"
            continue

        report = validate_app_spec(spec)
        last_report = report

        if report.ok:
            return PlanResult(
                spec=spec,
                report=report,
                attempts=attempt,
                provider=completion.provider,
                model=completion.model,
                input_tokens=totals["input"],
                output_tokens=totals["output"],
                cost_micros=totals["cost"],
            )

        last_problem = report.as_prompt_feedback()
        logger.info("planner attempt %s failed validation: %s", attempt, last_problem)
        messages = f"{prompt}\n\n{prompts.repair_prompt(last_problem)}"

    if source_description:
        # Rather than hand the user nothing, fall back to the closest template
        # and tell them that is what happened.
        logger.warning("planner gave up after %s attempts; using a template", MAX_ATTEMPTS)
        fallback = _offline_plan(source_description)
        fallback.attempts = MAX_ATTEMPTS
        return fallback

    raise PlanningError(
        "The plan could not be made valid after two attempts. "
        f"Last problem:\n{last_problem}",
        last_report,
    )


def _readable_pydantic_errors(exc: ValidationError, limit: int = 12) -> str:
    lines = []
    for error in exc.errors()[:limit]:
        where = ".".join(str(part) for part in error["loc"]) or "(top level)"
        lines.append(f"- {where}: {error['msg']}")
    if len(exc.errors()) > limit:
        lines.append(f"- ...and {len(exc.errors()) - limit} more")
    return "\n".join(lines)


_schema_cache: dict[str, Any] | None = None


def _app_schema() -> dict[str, Any]:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = AppSpec.model_json_schema()
    return _schema_cache


# --------------------------------------------------------------------------
# Offline planning
# --------------------------------------------------------------------------

#: Words that suggest which template fits. Crude keyword matching, but it means
#: the platform is demonstrable with no API key at all.
_TEMPLATE_HINTS: dict[str, tuple[str, ...]] = {
    "leave_management": (
        "leave", "holiday", "time off", "absence", "vacation", "sick",
        "attendance", "day off",
    ),
    "expense_approval": (
        "expense", "claim", "reimburse", "spend", "invoice", "bill",
        "purchase", "budget", "payment", "cost",
    ),
    "customer_complaints": (
        "complaint", "ticket", "support", "grievance", "issue", "customer",
        "helpdesk", "feedback", "service request", "query",
    ),
}


def choose_template(description: str) -> str:
    """The demo template whose words best match this description."""
    lowered = description.lower()
    scores = {
        name: sum(1 for hint in hints if hint in lowered)
        for name, hints in _TEMPLATE_HINTS.items()
    }
    best = max(scores, key=lambda name: scores[name])
    # Approval routing is the most common request, so it is the safe default.
    return best if scores[best] > 0 else "leave_management"


def _offline_plan(description: str) -> PlanResult:
    from app.specs.loader import load_template

    template = choose_template(description)
    spec = load_template(template)
    report = validate_app_spec(spec)
    return PlanResult(spec=spec, report=report, provider="echo", model="echo", offline=True)


# --------------------------------------------------------------------------
# Websites
# --------------------------------------------------------------------------


def plan_site(
    description: str,
    *,
    templates: list[str],
    themes: list[str],
    provider: AIProvider | None = None,
) -> SitePlanResult:
    """Fill in site content from a description."""
    description = description.strip()
    if len(description) < 10:
        raise PlanningError("Please say a little about yourself or your business.")

    provider = provider or get_provider()

    if isinstance(provider, EchoProvider):
        return SitePlanResult(
            spec=_offline_site(description, templates[0], themes[0]),
            provider="echo",
            model="echo",
            offline=True,
        )

    system = (
        f"{prompts.SITE_PLANNER_SYSTEM}\n"
        f"Templates: {', '.join(templates)}\n"
        f"Themes: {', '.join(themes)}\n"
    )

    last_problem = ""
    for _ in range(MAX_ATTEMPTS):
        completion = provider.complete(
            system=system,
            prompt=f"Write the site for:\n\n{description}",
            schema=SiteSpec.model_json_schema(),
            max_tokens=4000,
        )
        try:
            spec = SiteSpec.model_validate(completion.json())
        except (AIError, ValidationError) as exc:
            last_problem = str(exc)
            continue

        # Keep the model inside the choices that actually exist.
        if spec.template not in templates:
            spec.template = templates[0]
        if spec.theme not in themes:
            spec.theme = themes[0]

        return SitePlanResult(
            spec=spec,
            provider=completion.provider,
            model=completion.model,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            cost_micros=completion.cost_micros,
        )

    logger.warning("site planner failed, using a plain page: %s", last_problem)
    return SitePlanResult(
        spec=_offline_site(description, templates[0], themes[0]),
        provider="echo",
        model="echo",
        offline=True,
    )


def _offline_site(description: str, template: str, theme: str) -> SiteSpec:
    """A plain but real page built from the description itself."""
    first_line = description.strip().split("\n")[0]
    name = first_line[:60].rstrip(".,")
    return SiteSpec(
        template=template,
        theme=theme,
        site_name=name or "My Site",
        tagline=first_line[:80] or "Welcome",
        hero_body=description[:600],
        sections=[],
        cta_label="Get in touch",
    )
