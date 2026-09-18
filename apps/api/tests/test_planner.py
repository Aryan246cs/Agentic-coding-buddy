"""Planner tests, driven by a scripted provider.

The planner's job is not to be clever — it is to never hand the rest of the
system something invalid. These tests script exactly what a model returns
(including the ways models actually misbehave) and check that the retry,
validation and fallback all hold. No network, no key, no cost.
"""

from __future__ import annotations

import json

import pytest

from app.ai.planner import PlanningError, plan_app, revise_app
from app.ai.provider import AIError, Completion, EchoProvider, parse_json
from app.specs.loader import load_template
from app.specs.validator import validate_app_spec


class ScriptedProvider:
    """Returns each scripted answer in turn, then repeats the last one."""

    name = "scripted"

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = 0
        self.prompts = []

    def complete(self, *, system, prompt, schema=None, max_tokens=8000, fast=False):
        del system, schema, max_tokens, fast
        self.prompts.append(prompt)
        answer = self.answers[min(self.calls, len(self.answers) - 1)]
        self.calls += 1
        if isinstance(answer, Exception):
            raise answer
        return Completion(
            text=answer if isinstance(answer, str) else json.dumps(answer),
            provider=self.name,
            model="scripted",
            input_tokens=1000,
            output_tokens=500,
        )

    def classify(self, text, categories):
        return categories[0]


@pytest.fixture
def good_spec() -> dict:
    return load_template("leave_management").model_dump(mode="json")


# --------------------------------------------------------------------------
# The happy path
# --------------------------------------------------------------------------


def test_a_valid_answer_is_returned_on_the_first_try(good_spec):
    provider = ScriptedProvider(good_spec)

    result = plan_app("Staff request leave and their manager approves it.", provider)

    assert provider.calls == 1
    assert result.attempts == 1
    assert result.offline is False
    assert result.report.ok
    assert result.spec.name == "Employee Leave Management"
    assert result.input_tokens == 1000


def test_cost_is_measured_even_though_nothing_is_charged_yet(good_spec):
    provider = ScriptedProvider(good_spec)
    result = plan_app("Staff request leave and their manager approves it.", provider)

    # The scripted model reports no price, so the estimate is zero — but the
    # token counts are real and that is what the billing decision needs.
    assert result.input_tokens == 1000
    assert result.output_tokens == 500
    assert result.cost_micros == 0


# --------------------------------------------------------------------------
# The ways models actually misbehave
# --------------------------------------------------------------------------


def test_json_wrapped_in_prose_and_fences_is_still_read(good_spec):
    wrapped = (
        "Sure! Here is the configuration you asked for:\n\n"
        f"```json\n{json.dumps(good_spec)}\n```\n\nLet me know if you need changes."
    )
    provider = ScriptedProvider(wrapped)

    result = plan_app("Staff request leave and their manager approves it.", provider)

    assert provider.calls == 1
    assert result.spec.name == "Employee Leave Management"


def test_an_invalid_spec_is_sent_back_with_its_errors_and_fixed(good_spec):
    broken = json.loads(json.dumps(good_spec))
    broken["screens"][0]["entity"] = "does_not_exist"

    provider = ScriptedProvider(broken, good_spec)

    result = plan_app("Staff request leave and their manager approves it.", provider)

    assert provider.calls == 2
    assert result.attempts == 2
    assert result.report.ok

    # The second prompt actually told the model what was wrong.
    assert "does_not_exist" in provider.prompts[1]
    assert "not valid" in provider.prompts[1]

    # Both attempts were paid for, and both are counted.
    assert result.input_tokens == 2000


def test_a_malformed_shape_is_reported_in_readable_terms(good_spec):
    broken = json.loads(json.dumps(good_spec))
    broken["roles"] = "not a list at all"

    provider = ScriptedProvider(broken, good_spec)
    result = plan_app("Staff request leave and their manager approves it.", provider)

    assert provider.calls == 2
    assert result.report.ok
    assert "roles" in provider.prompts[1]


def test_unparseable_output_is_retried(good_spec):
    provider = ScriptedProvider("I'm afraid I can't help with that.", good_spec)

    result = plan_app("Staff request leave and their manager approves it.", provider)

    assert provider.calls == 2
    assert result.report.ok


# --------------------------------------------------------------------------
# When it cannot be fixed
# --------------------------------------------------------------------------


def test_two_bad_answers_fall_back_to_the_closest_template(good_spec):
    broken = json.loads(json.dumps(good_spec))
    broken["screens"][0]["entity"] = "does_not_exist"
    provider = ScriptedProvider(broken, broken)

    result = plan_app("Staff want to claim their travel expenses back.", provider)

    assert provider.calls == 2
    assert result.offline is True
    assert result.report.ok  # whatever we hand back is always valid
    assert "expense" in result.spec.name.lower()
    assert "did not hold together" in result.fallback_reason


def test_an_unreachable_provider_falls_back_instead_of_dead_ending():
    """A provider outage must not leave the user with nothing."""
    provider = ScriptedProvider(AIError("Groq could not be reached: 401 invalid key"))

    result = plan_app("Staff request leave and their manager approves it.", provider)

    # Asked once, then stopped — retrying a bad key is pointless.
    assert provider.calls == 1
    assert result.offline is True
    assert "leave" in result.spec.name.lower()
    assert "could not reach the AI" in result.fallback_reason


def test_the_fallback_picks_the_template_that_matches_the_words():
    provider = ScriptedProvider(AIError("down"))

    leave = plan_app("Our staff need to book time off and get it approved.", provider)
    expenses = plan_app("People spend their own money and claim it back.", provider)
    complaints = plan_app("Customers write in when something goes wrong.", provider)

    assert "leave" in leave.spec.name.lower()
    assert "expense" in expenses.spec.name.lower()
    assert "complaint" in complaints.spec.name.lower()


def test_a_description_too_short_to_act_on_is_refused():
    with pytest.raises(PlanningError, match="describe your process"):
        plan_app("leave", ScriptedProvider({}))


# --------------------------------------------------------------------------
# Revising
# --------------------------------------------------------------------------


def test_a_revision_returns_the_changed_spec(good_spec):
    changed = json.loads(json.dumps(good_spec))
    changed["name"] = "Leave, with HR"
    provider = ScriptedProvider(changed)

    result = revise_app(load_template("leave_management"), "rename it", provider)

    assert result.spec.name == "Leave, with HR"
    # The model was shown the current configuration to change.
    assert "leave_requests" in provider.prompts[0]


def test_a_revision_never_falls_back_to_a_template(good_spec):
    """Changing an app must change that app, or fail — never swap it out."""
    provider = ScriptedProvider(AIError("provider down"))

    with pytest.raises(PlanningError, match="could not be reached"):
        revise_app(load_template("leave_management"), "add an HR step", provider)


def test_a_revision_that_stays_invalid_raises_with_the_reasons(good_spec):
    broken = json.loads(json.dumps(good_spec))
    broken["workflows"][0]["steps"][1]["on_approve"] = "no_such_step"
    provider = ScriptedProvider(broken, broken)

    with pytest.raises(PlanningError) as caught:
        revise_app(load_template("leave_management"), "change something", provider)

    assert "no_such_step" in str(caught.value)
    assert caught.value.report is not None


# --------------------------------------------------------------------------
# The offline planner
# --------------------------------------------------------------------------


def test_the_offline_planner_returns_a_valid_app():
    result = plan_app("Staff request leave, manager approves.", EchoProvider())

    assert result.offline is True
    assert validate_app_spec(result.spec).ok


def test_the_offline_classifier_spots_an_urgent_complaint():
    echo = EchoProvider()
    urgent = echo.classify(
        "My order never arrived and I want a refund immediately",
        ["Urgent", "Normal", "Low"],
    )
    ordinary = echo.classify("The colour is slightly different", ["Urgent", "Normal", "Low"])

    assert urgent == "Urgent"
    assert ordinary == "Normal"


def test_revising_offline_says_what_is_needed():
    with pytest.raises(PlanningError, match="ANTHROPIC_API_KEY"):
        revise_app(load_template("leave_management"), "add a step", EchoProvider())


# --------------------------------------------------------------------------
# JSON extraction
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('```json\n{"a": 1}\n```', {"a": 1}),
        ('```\n{"a": 1}\n```', {"a": 1}),
        ('Here you go: {"a": 1} — hope that helps!', {"a": 1}),
        ('  \n {"a": [1, 2]} \n ', {"a": [1, 2]}),
    ],
)
def test_parse_json(text, expected):
    assert parse_json(text) == expected


def test_parse_json_gives_up_on_genuine_rubbish():
    with pytest.raises(AIError, match="usable JSON"):
        parse_json("I am not going to answer that.")
