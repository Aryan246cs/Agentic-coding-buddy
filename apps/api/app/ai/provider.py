"""The AI seam.

One interface, three implementations. Everything above this file asks for
"JSON matching this schema" and does not care who answered, which is what
makes the provider a configuration choice rather than an architectural one.

  * `AnthropicProvider` — the one to prefer; structured output is reliable.
  * `GroqProvider`      — what this project already had a key for.
  * `EchoProvider`      — no key needed. Returns a hand-built spec so the whole
                          product can be developed and demoed offline.

Token usage comes back with every call so cost per generation is known from
the first day, long before anything is charged for.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    """The provider could not be reached, or would not answer usefully."""


@dataclass
class Completion:
    """One answer, plus what it cost."""

    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    #: Rupees per million tokens, so cost can be shown in the user's currency.
    _RUPEES_PER_USD = 88

    @property
    def cost_micros(self) -> int:
        """Cost in micro-rupees. Integers only — no float money."""
        rates = _PRICE_PER_MTOK_USD.get(self.model)
        if not rates:
            return 0
        usd = (
            self.input_tokens * rates[0] + self.output_tokens * rates[1]
        ) / 1_000_000
        return int(usd * self._RUPEES_PER_USD * 1_000_000)

    def json(self) -> Any:
        """The answer parsed as JSON, tolerating the wrappers models add."""
        return parse_json(self.text)


#: (input, output) USD per million tokens. Used only to show an estimate, so
#: being a little stale is fine; being absent just means no estimate.
_PRICE_PER_MTOK_USD: dict[str, tuple[float, float]] = {
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "openai/gpt-oss-120b": (0.15, 0.75),
    "llama-3.3-70b-versatile": (0.59, 0.79),
}

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json(text: str) -> Any:
    """Pull JSON out of a model's answer.

    Models wrap JSON in prose or code fences even when told not to, and that
    is not worth failing a user's build over. Anything beyond this — truncated
    or genuinely malformed — is a real error and is raised.
    """
    candidate = text.strip()

    fenced = _FENCE_RE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Fall back to the outermost {...} or [...] in the text.
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = candidate.find(opener), candidate.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise AIError("The model did not return usable JSON.")


# --------------------------------------------------------------------------
# Providers
# --------------------------------------------------------------------------


class AIProvider(ABC):
    name: str

    @abstractmethod
    def complete(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 8000,
        fast: bool = False,
    ) -> Completion:
        """Answer `prompt`. When `schema` is given, the answer must be JSON."""

    def classify(self, text: str, categories: list[str]) -> str:
        """Sort `text` into one of `categories`.

        Shared by every provider because the prompt is the same and the answer
        is validated against the list either way.
        """
        options = ", ".join(categories)
        completion = self.complete(
            system=(
                "You sort messages into exactly one category. Reply with the "
                "category name alone — no explanation, no punctuation."
            ),
            prompt=f"Categories: {options}\n\nMessage:\n{text[:4000]}\n\nCategory:",
            max_tokens=24,
            fast=True,
        )

        answer = completion.text.strip().strip(".\"'").lower()
        for category in categories:
            if answer == category.lower():
                return category
        # A model that pads its answer ("Category: Urgent") still gets read.
        for category in categories:
            if category.lower() in answer:
                return category

        raise AIError(
            f"Could not read '{completion.text.strip()[:60]}' as one of: {options}"
        )


class EchoProvider(AIProvider):
    """A provider that needs no API key.

    Not a mock for tests — it is how the platform stays fully usable with no
    credentials at all, which keeps the runtime honest: if the product only
    works when an AI is reachable, the architecture is wrong.
    """

    name = "echo"

    def __init__(self) -> None:
        self.model = "echo"

    def complete(self, *, system, prompt, schema=None, max_tokens=8000, fast=False):
        del system, schema, max_tokens, fast
        return Completion(text=prompt, provider=self.name, model=self.model)

    def classify(self, text: str, categories: list[str]) -> str:
        """Pick a category by keyword, falling back to the middle option.

        Crude on purpose. It makes the complaints demo behave sensibly offline
        without pretending to be intelligent.
        """
        lowered = text.lower()
        urgent_words = (
            "urgent", "immediately", "asap", "angry", "refund", "broken",
            "never arrived", "worst", "unacceptable", "legal", "fraud",
        )
        if any(word in lowered for word in urgent_words):
            for category in categories:
                if category.lower() in ("urgent", "high", "critical"):
                    return category
        return categories[len(categories) // 2]


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, settings: Settings):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise AIError(
                "The anthropic package is not installed. Run: uv sync --extra claude"
            ) from exc

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.fast_model = settings.anthropic_fast_model

    def complete(self, *, system, prompt, schema=None, max_tokens=8000, fast=False):
        model = self.fast_model if fast else self.model
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        if schema is not None:
            request["output_config"] = {
                "format": {
                    "type": "json_schema",
                    "schema": schema,
                }
            }

        try:
            response = self._client.messages.create(**request)
        except Exception as exc:  # noqa: BLE001 - surfaced to the user as one error
            raise AIError(f"Claude could not be reached: {exc}") from exc

        if getattr(response, "stop_reason", None) == "refusal":
            raise AIError("Claude declined to answer this request.")

        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        return Completion(
            text=text,
            provider=self.name,
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self, settings: Settings):
        try:
            from groq import Groq
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise AIError("The groq package is not installed.") from exc

        self._client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def complete(self, *, system, prompt, schema=None, max_tokens=8000, fast=False):
        del fast  # one model configured, so nothing to switch to
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        if schema is not None:
            # Groq's JSON mode guarantees valid JSON but not schema adherence,
            # so the validator downstream is doing the real work here.
            request["response_format"] = {"type": "json_object"}

        try:
            response = self._client.chat.completions.create(**request)
        except Exception as exc:  # noqa: BLE001
            raise AIError(f"Groq could not be reached: {exc}") from exc

        usage = response.usage
        return Completion(
            text=response.choices[0].message.content or "",
            provider=self.name,
            model=self.model,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )


@dataclass
class _ProviderCache:
    instance: AIProvider | None = None
    key: str = ""


_cache: _ProviderCache = _ProviderCache()


def get_provider(settings: Settings | None = None) -> AIProvider:
    """The provider the current configuration can actually use."""
    settings = settings or get_settings()
    choice = settings.resolved_provider

    if _cache.instance is not None and _cache.key == choice:
        return _cache.instance

    match choice:
        case "anthropic":
            provider: AIProvider = AnthropicProvider(settings)
        case "groq":
            provider = GroqProvider(settings)
        case _:
            logger.warning(
                "No AI key configured — using the offline planner. Set "
                "ANTHROPIC_API_KEY or GROQ_API_KEY for real generation."
            )
            provider = EchoProvider()

    _cache.instance = provider
    _cache.key = choice
    return provider
