from app.ai.site_agents import _normalize_site_payload
from app.ai.site_agents import build_custom_site
from app.ai.provider import Completion, GroqProvider
from app.specs.schema import SiteSpec
import json


def test_normalize_site_payload_repairs_alternate_section_shape():
    payload = _normalize_site_payload({
        "name": "Robin's Birthday",
        "headline": "Happy Birthday Robin!",
        "sections": [
            {"id": "header", "type": "hero", "title": "", "subtitle": "Wishing you joy"},
            {"id": "todo", "title": "", "text": "Made with love for Robin"},
            {"type": "add", "title": "Photos", "images": ["/images/birthday.jpg"]},
        ],
    })

    spec = SiteSpec.model_validate({**payload, "template": "custom"})

    assert spec.site_name == "Robin's Birthday"
    assert spec.tagline == "Happy Birthday Robin!"
    assert [section.key for section in spec.sections] == ["header", "todo", "add"]
    assert spec.sections[0].body == "Wishing you joy"
    assert spec.sections[1].body == "Made with love for Robin"


def test_normalize_site_payload_accepts_camel_case_site_name():
    payload = _normalize_site_payload({"siteName": "Mantra", "tagline": "Find your center"})

    spec = SiteSpec.model_validate({**payload, "template": "custom"})

    assert spec.site_name == "Mantra"


def test_custom_site_pipeline_reaches_real_compiler():
    class ScriptedProvider:
        name = "scripted"

        def __init__(self):
            self.answers = [
                {
                    "site_name": "Robin's Birthday", "tagline": "A day full of joy",
                    "sections": [{"id": "party", "title": "Celebrate", "subtitle": "Made with love."}],
                },
                {"design_direction": "Warm celebratory page", "page_sections": ["Hero", "Celebrate"], "interaction_notes": [], "quality_checks": ["Responsive"]},
                {"App.tsx": "export default function Site() { return <main className='p-8'><h1>Happy Birthday</h1></main> }", "styles.css": ""},
                {"approved": True, "feedback": "Ready"},
            ]
            self.calls = 0

        def complete(self, *, system, prompt, schema=None, max_tokens=8000, fast=False):
            del system, prompt, schema, max_tokens, fast
            value = self.answers[self.calls]
            self.calls += 1
            return Completion(json.dumps(value), self.name, "scripted", 10, 10)

    provider = ScriptedProvider()
    result = build_custom_site("A joyful birthday website for Robin with a warm celebratory style.", provider)

    assert provider.calls == 4
    assert result.spec.site_name == "Robin's Birthday"
    assert result.spec.sections[0].key == "party"
    assert result.agent_log[-1] == {"role": "Build verifier", "status": "passed"}
    assert result.files["app.js"]
    assert result.files["site.css"]


def test_groq_retries_json_validation_failure_without_json_mode():
    class BadRequest(Exception):
        body = {"error": {"code": "json_validate_failed"}}

    class Completions:
        def __init__(self):
            self.requests = []

        def create(self, **request):
            self.requests.append(request)
            if len(self.requests) == 1:
                raise BadRequest("invalid generated JSON")
            return type("Response", (), {
                "choices": [type("Choice", (), {"message": type("Message", (), {"content": '{"ok":true}'})()})()],
                "usage": type("Usage", (), {"prompt_tokens": 1, "completion_tokens": 1})(),
            })()

    completions = Completions()
    provider = GroqProvider.__new__(GroqProvider)
    provider.model = "test-model"
    provider._client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()

    result = provider.complete(system="Return JSON", prompt="Plan", schema={"type": "object"})

    assert result.json() == {"ok": True}
    assert completions.requests[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in completions.requests[1]
    assert "exactly one valid JSON object" in completions.requests[1]["messages"][-1]["content"]


def test_custom_site_pipeline_recovers_when_reviewer_omits_feedback():
    class ScriptedProvider:
        name = "scripted"

        def __init__(self):
            self.answers = [
                {"site_name": "Robin's Birthday", "tagline": "A day full of joy", "sections": []},
                {"design_direction": "Warm celebratory page", "page_sections": ["Hero"], "interaction_notes": [], "quality_checks": ["Responsive"]},
                {"App.tsx": "export default function Site() { return <main className='p-8'><h1>Happy Birthday</h1></main> }", "styles.css": ""},
                {"approved": False},
            ]

        def complete(self, *, system, prompt, schema=None, max_tokens=8000, fast=False):
            del system, prompt, schema, max_tokens, fast
            return Completion(json.dumps(self.answers.pop(0)), self.name, "scripted", 10, 10)

    result = build_custom_site("A joyful birthday website for Robin with a warm celebratory style.", ScriptedProvider())

    assert len(result.agent_log) == 5
    assert result.agent_log[-1] == {"role": "Build verifier", "status": "passed"}
