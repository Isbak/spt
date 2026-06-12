"""Writable workspace configuration: model choice and the domain↔git registry.

Persisted as JSON under ``settings.workspace_root`` (``platform_config.json``). The
model section is read back by :func:`semantic_platform.config.load_settings` as a
layer *below* environment variables, so a choice made in the setup UI survives a
restart without editing ``.env`` while env still wins. Domain references associate a
*domain of interest* with the separate git repository its model is authored in.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re

from semantic_platform.config import PLATFORM_CONFIG_FILENAME, Settings, load_settings

SUPPORTED_PROVIDERS = ("auto", "local", "anthropic", "ollama", "openai")
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
_ID_RE = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class ModelConfig:
    """The persisted LLM provider selection surfaced by the setup UI."""

    provider: str
    model: str | None
    ollama_base_url: str


@dataclass(frozen=True)
class DomainRef:
    """A domain of interest mapped to the separate git repo its model lives in."""

    domain_id: str
    label: str
    remote_url: str
    branch: str
    local_path: str
    token_env: str | None


def slugify(value: str) -> str:
    """Return a filesystem/branch-safe identifier derived from ``value``."""
    slug = _ID_RE.sub("-", value.strip().lower()).strip("-")
    return slug or "domain"


def _config_path(settings: Settings) -> "object":
    return settings.workspace_root / PLATFORM_CONFIG_FILENAME


def load_raw(settings: Settings | None = None) -> dict:
    """Return the raw workspace config document (empty dict when absent)."""
    settings = settings or load_settings()
    path = _config_path(settings)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - corrupt/unreadable file
        return {}
    return data if isinstance(data, dict) else {}


def save_raw(data: dict, settings: Settings | None = None) -> None:
    """Write the raw workspace config document, creating the workspace dir."""
    settings = settings or load_settings()
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    _config_path(settings).write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


# --- model configuration ---------------------------------------------------


def get_model_config(settings: Settings | None = None) -> ModelConfig:
    """Return the persisted model configuration (falling back to defaults)."""
    settings = settings or load_settings()
    data = load_raw(settings)
    return ModelConfig(
        provider=(data.get("llm_provider") or settings.llm_provider or "local"),
        model=data.get("llm_model") or settings.llm_model,
        ollama_base_url=data.get("ollama_base_url") or DEFAULT_OLLAMA_BASE_URL,
    )


def set_model_config(
    provider: str,
    model: str | None = None,
    ollama_base_url: str | None = None,
    settings: Settings | None = None,
) -> ModelConfig:
    """Persist and return the model configuration.

    Raises ``ValueError`` for an unsupported provider. API keys are never stored
    here — they are read from the environment only.
    """
    provider = provider.strip().lower()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported provider {provider!r}; expected one of {SUPPORTED_PROVIDERS}.")
    settings = settings or load_settings()
    data = load_raw(settings)
    data["llm_provider"] = provider
    data["llm_model"] = model or None
    data["ollama_base_url"] = ollama_base_url or DEFAULT_OLLAMA_BASE_URL
    save_raw(data, settings)
    return get_model_config(settings)


# --- domain registry -------------------------------------------------------


def _to_domain(record: dict, settings: Settings) -> DomainRef:
    domain_id = str(record["domain_id"])
    default_path = settings.workspace_root / "domains" / domain_id
    return DomainRef(
        domain_id=domain_id,
        label=record.get("label") or domain_id,
        remote_url=record.get("remote_url", ""),
        branch=record.get("branch") or "main",
        local_path=record.get("local_path") or str(default_path),
        token_env=record.get("token_env") or None,
    )


def list_domains(settings: Settings | None = None) -> list[DomainRef]:
    """Return all configured domain references."""
    settings = settings or load_settings()
    records = load_raw(settings).get("domains", [])
    return [_to_domain(record, settings) for record in records if record.get("domain_id")]


def get_domain(domain_id: str, settings: Settings | None = None) -> DomainRef | None:
    """Return a single domain reference, or ``None`` when not configured."""
    return next((d for d in list_domains(settings) if d.domain_id == domain_id), None)


def add_domain(
    label: str,
    remote_url: str,
    branch: str = "main",
    token_env: str | None = None,
    domain_id: str | None = None,
    settings: Settings | None = None,
) -> DomainRef:
    """Add (or update) a domain reference and return it."""
    settings = settings or load_settings()
    domain_id = slugify(domain_id or label)
    data = load_raw(settings)
    domains = [d for d in data.get("domains", []) if d.get("domain_id") != domain_id]
    domains.append(
        {
            "domain_id": domain_id,
            "label": label.strip() or domain_id,
            "remote_url": remote_url.strip(),
            "branch": branch.strip() or "main",
            "local_path": str(settings.workspace_root / "domains" / domain_id),
            "token_env": (token_env or "").strip() or None,
        }
    )
    data["domains"] = domains
    save_raw(data, settings)
    return _to_domain(domains[-1], settings)


def remove_domain(domain_id: str, settings: Settings | None = None) -> bool:
    """Remove a domain reference; return ``True`` when one was removed."""
    settings = settings or load_settings()
    data = load_raw(settings)
    before = data.get("domains", [])
    after = [d for d in before if d.get("domain_id") != domain_id]
    if len(after) == len(before):
        return False
    data["domains"] = after
    save_raw(data, settings)
    return True
