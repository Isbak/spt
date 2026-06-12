"""Pluggable language models for the governed agent assist.

Two **self-contained** providers need no API key and no third-party cloud:

* ``local`` (default) — a free, offline, deterministic model. No process, no
  network; runs anywhere, including CI.
* ``ollama`` — a real local LLM served by the bundled Ollama container
  (``docker compose --profile llm up``), the LLM counterpart to the bundled
  Fuseki triple store. Free and self-hosted; talks plain HTTP.

The **external** providers — ``anthropic`` and ``openai`` — call third-party cloud
APIs and require credentials. All providers are selected via ``LLM_PROVIDER`` /
``LLM_MODEL`` and import their SDK lazily, so a provider's dependency is only
needed when it is actually used.

These models only ever turn a prompt into text. They never choose tools, write to
the knowledge graph, or drive agent plans — that boundary is enforced by the
governed assist in :mod:`semantic_platform.agents.assist`.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Protocol, runtime_checkable

from semantic_platform.config import Settings, load_settings

DEFAULT_ANTHROPIC_MODEL = "claude-opus-4-8"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_MODEL = "llama3.2"

#: Providers presented as first-class in the UI and tried, in order, by ``auto``.
AUTO_PROVIDER_ORDER = ("anthropic", "ollama", "local")


@dataclass(frozen=True)
class LLMCompletion:
    """A single text completion plus the model/provider that produced it."""

    text: str
    provider: str
    model_id: str


@runtime_checkable
class LanguageModel(Protocol):
    """A read-only text generator used by the governed agent assist."""

    provider: str
    model_id: str

    def complete(self, prompt: str, *, system: str | None = None) -> LLMCompletion:
        """Return a completion for ``prompt`` (optionally guided by ``system``)."""


class LocalDeterministicModel:
    """Free, offline default: a deterministic extractive summary of the prompt.

    It performs no inference and makes no network calls — it digests the fact
    lines already present in the prompt into a stable, readable summary. This
    keeps the assist fully self-contained and reproducible by default.
    """

    provider = "local"
    model_id = "local-deterministic"

    def complete(self, prompt: str, *, system: str | None = None) -> LLMCompletion:
        facts = [line.strip() for line in prompt.splitlines() if line.strip().startswith("- ")]
        if facts:
            shown = facts[:8]
            body = "\n".join(shown)
            more = "" if len(facts) <= 8 else f"\n- … and {len(facts) - 8} more fact(s)"
            text = f"Summary of {len(facts)} fact(s):\n{body}{more}"
        else:
            text = "No facts were available in the permitted scope."
        return LLMCompletion(text=text, provider=self.provider, model_id=self.model_id)


class AnthropicModel:
    """External provider backed by the Anthropic API (lazy import)."""

    provider = "anthropic"

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or DEFAULT_ANTHROPIC_MODEL

    def complete(self, prompt: str, *, system: str | None = None) -> LLMCompletion:  # pragma: no cover - network
        import anthropic

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=self.model_id,
            max_tokens=1024,
            system=system or "You explain knowledge-graph facts faithfully and concisely.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return LLMCompletion(text=text, provider=self.provider, model_id=self.model_id)


class OpenAIModel:
    """External provider backed by the OpenAI API (lazy import)."""

    provider = "openai"

    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or DEFAULT_OPENAI_MODEL

    def complete(self, prompt: str, *, system: str | None = None) -> LLMCompletion:  # pragma: no cover - network
        import openai

        client = openai.OpenAI()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(model=self.model_id, messages=messages)
        text = response.choices[0].message.content or ""
        return LLMCompletion(text=text, provider=self.provider, model_id=self.model_id)


class OllamaModel:
    """Self-contained provider backed by the bundled local Ollama server over HTTP.

    Free and self-hosted (no API key, no cloud) — the LLM analogue of the bundled
    Fuseki service. Defaults to the ``ollama`` compose service / ``localhost:11434``.
    """

    provider = "ollama"

    def __init__(self, base_url: str | None = None, model_id: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model_id = model_id or DEFAULT_OLLAMA_MODEL

    def complete(self, prompt: str, *, system: str | None = None) -> LLMCompletion:
        import requests

        payload = {"model": self.model_id, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        text = response.json().get("response", "")
        return LLMCompletion(text=text, provider=self.provider, model_id=self.model_id)


def anthropic_configured() -> bool:
    """Return ``True`` when an Anthropic API key is available in the environment."""
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def ollama_reachable(base_url: str | None = None, *, timeout: float = 1.0) -> bool:
    """Return ``True`` when a local Ollama server answers on its base URL."""
    url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
    try:  # pragma: no cover - network probe
        import requests

        return requests.get(url, timeout=timeout).ok
    except Exception:  # pragma: no cover - server absent / requests missing
        return False


def resolve_language_model(settings: Settings | None = None) -> LanguageModel:
    """Resolve the configured language model (default: free offline ``local``).

    Provider classes import their SDK lazily, so selecting an external provider
    here does not require its dependency until ``complete`` is actually called.
    The ``auto`` provider makes Anthropic and Ollama first-class: it uses
    Anthropic when an API key is set, else a reachable local Ollama, else the
    offline ``local`` model — so the platform always resolves to *something*.
    """
    settings = settings or load_settings()
    provider = settings.llm_provider
    if provider == "auto":
        if anthropic_configured():
            return AnthropicModel(settings.llm_model)
        if ollama_reachable():
            return OllamaModel(model_id=settings.llm_model)
        return LocalDeterministicModel()
    if provider in ("", "local", "none"):
        return LocalDeterministicModel()
    if provider == "anthropic":
        return AnthropicModel(settings.llm_model)
    if provider == "openai":
        return OpenAIModel(settings.llm_model)
    if provider == "ollama":
        return OllamaModel(model_id=settings.llm_model)
    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider!r} (expected auto, local, anthropic, openai, or ollama)"
    )
