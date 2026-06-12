"""Guided, governed authoring conversation.

Ties the pieces together: resolve the selected domain's git workspace, talk to the
human (via the configured language model) to gather requirements, scaffold the model
files, write them into a sandboxed branch, validate them, and PROV-record the turn.
Nothing is written to the platform's own graph; review happens through a Pull Request.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import UTC, datetime

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import PROV, RDF, XSD

from semantic_platform.agents.llm import LanguageModel, resolve_language_model
from semantic_platform.authoring import workspace_config as wc
from semantic_platform.authoring.gitrepo import GitRepo, PullRequestRef, open_pull_request
from semantic_platform.authoring.scaffold import FilePlan, InterviewAnswers, scaffold_model
from semantic_platform.config import Settings, load_settings
from semantic_platform.validate import validate_rdf_syntax

AUTHORING = Namespace("https://example.org/semantic-platform/authoring#")

STATUS_NEEDS_DOMAIN = "needs_domain_setup"
STATUS_QUESTION = "question"
STATUS_DRAFTED = "drafted"


@dataclass(frozen=True)
class AuthoringResult:
    """Outcome of a single authoring turn."""

    domain_id: str | None
    status: str
    reply: str
    files: tuple[str, ...] = ()
    branch: str | None = None
    validation_ok: bool | None = None
    validation_report: str = ""
    provider: str = ""
    model_id: str = ""
    provenance: Graph | None = field(default=None)


def _branch_for(domain_id: str) -> str:
    return f"authoring/{domain_id}"


def _record_provenance(domain_id: str, files: tuple[str, ...], provider: str, model_id: str) -> Graph:
    graph = Graph()
    graph.bind("prov", PROV)
    graph.bind("authoring", AUTHORING)
    now = datetime.now(UTC).replace(microsecond=0)
    activity = URIRef(AUTHORING[f"authoring-{domain_id}-{now.strftime('%Y%m%dT%H%M%SZ')}"])
    graph.add((activity, RDF.type, AUTHORING.AuthoringActivity))
    graph.add((activity, RDF.type, PROV.Activity))
    graph.add((activity, AUTHORING.domain, Literal(domain_id)))
    graph.add((activity, AUTHORING.usedProvider, Literal(provider)))
    graph.add((activity, AUTHORING.usedModel, Literal(model_id)))
    graph.add((activity, AUTHORING.fileCount, Literal(len(files), datatype=XSD.integer)))
    graph.add((activity, PROV.endedAtTime, Literal(now.isoformat(), datatype=XSD.dateTime)))
    for path in files:
        entity = URIRef(AUTHORING[f"file-{path}"])
        graph.add((entity, RDF.type, PROV.Entity))
        graph.add((entity, PROV.wasGeneratedBy, activity))
    return graph


def _setup_prompt(settings: Settings) -> AuthoringResult:
    return AuthoringResult(
        domain_id=None,
        status=STATUS_NEEDS_DOMAIN,
        reply=(
            "No domain repository is configured yet. To start modelling, open "
            "Settings → Domain Repos and associate a git repository with the domain "
            "you want to model. Then come back here and I'll scaffold it for you."
        ),
    )


def author_model(
    domain_id: str,
    answers: InterviewAnswers,
    *,
    settings: Settings | None = None,
) -> AuthoringResult:
    """Scaffold, write, validate and commit a model into the domain's sandbox branch."""
    settings = settings or load_settings()
    domain = wc.get_domain(domain_id, settings)
    if domain is None:
        return _setup_prompt(settings)

    plan: FilePlan = scaffold_model(answers)
    repo = GitRepo.clone_or_open(domain.local_path, domain.remote_url)
    branch = _branch_for(domain_id)
    repo.checkout_branch(branch)
    for relative_path, content in plan.files.items():
        repo.write_file(relative_path, content)

    syntax = validate_rdf_syntax(paths=[repo.path / "rdf"], settings=settings)
    ok = all(result.valid for result in syntax)
    report = "\n".join(f"{'OK ' if r.valid else 'ERR'} {r.path.name} {r.message}".rstrip() for r in syntax)
    repo.commit(f"Scaffold {answers.domain_label} model ({len(plan.files)} file(s))")

    files = tuple(plan.files)
    provenance = _record_provenance(domain_id, files, "scaffold", "deterministic")
    reply = (
        f"Drafted {len(files)} file(s) for **{answers.domain_label}** on branch `{branch}`: "
        + ", ".join(files)
        + (". Validation passed." if ok else ". Validation reported issues — see the report.")
        + " Review and open a Pull Request when ready."
    )
    return AuthoringResult(
        domain_id=domain_id,
        status=STATUS_DRAFTED,
        reply=reply,
        files=files,
        branch=branch,
        validation_ok=ok,
        validation_report=report,
        provider="scaffold",
        model_id="deterministic",
        provenance=provenance,
    )


def chat_turn(
    domain_id: str | None,
    message: str,
    history: list[dict] | None = None,
    *,
    settings: Settings | None = None,
    model: LanguageModel | None = None,
) -> AuthoringResult:
    """Hold a clarifying conversation about modelling the selected domain."""
    settings = settings or load_settings()
    if not domain_id or wc.get_domain(domain_id, settings) is None:
        return _setup_prompt(settings)

    model = model or resolve_language_model(settings)
    history_text = "\n".join(f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in (history or []))
    prompt = (
        "You are helping a human design an RDF/OWL knowledge model for a domain. "
        "Ask focused clarifying questions about the key classes, properties and "
        "relationships needed, one step at a time. Do not write code.\n\n"
        f"Domain: {domain_id}\n{history_text}\nuser: {message}"
    )
    completion = model.complete(prompt)
    return AuthoringResult(
        domain_id=domain_id,
        status=STATUS_QUESTION,
        reply=completion.text,
        provider=completion.provider,
        model_id=completion.model_id,
    )


def open_pr(
    domain_id: str,
    *,
    title: str | None = None,
    body: str | None = None,
    settings: Settings | None = None,
) -> PullRequestRef:
    """Push the domain's authoring branch and open (or link) a Pull Request."""
    settings = settings or load_settings()
    domain = wc.get_domain(domain_id, settings)
    if domain is None:
        raise KeyError(domain_id)
    branch = _branch_for(domain_id)
    repo = GitRepo.clone_or_open(domain.local_path, domain.remote_url)
    repo.commit(f"Authoring updates for {domain.label}")
    try:
        repo.push(branch, domain.token_env)
        pushed = True
    except Exception:  # pragma: no cover - depends on the configured remote
        pushed = False
    ref = open_pull_request(
        domain.remote_url,
        branch,
        domain.branch,
        title or f"Model updates: {domain.label}",
        body or "Generated by the governed authoring studio for review.",
        domain.token_env,
    )
    if pushed:
        # Push succeeded — reflect that even when the remote is not GitHub (no
        # compare URL / opened PR), instead of reporting it as a local-only commit.
        if ref.pull_request_url is None and ref.compare_url is None:
            return dataclasses.replace(
                ref, pushed=True, message=f"Branch '{branch}' pushed. Open a PR on your git host to review."
            )
        return dataclasses.replace(ref, pushed=True)
    if ref.pull_request_url is None and ref.compare_url is None:
        return PullRequestRef(branch, False, None, None, "Committed locally; configure a git remote to open a PR.")
    return ref
