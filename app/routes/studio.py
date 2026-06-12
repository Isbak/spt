"""Knowledge-modelling studio: folder tree, editor, and the authoring conversation."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, jsonify, render_template, request
from rdflib import RDF, Namespace

from semantic_platform.api import (
    authoring_chat,
    authoring_generate,
    commit_and_open_pr,
    get_model_config,
    list_domains,
    query_workspace,
    read_workspace_file,
    search_workspace,
    validate_workspace,
    workspace_analytics,
    workspace_diff,
    workspace_status,
    workspace_tree,
    write_workspace_file,
)
from semantic_platform.authoring.gitrepo import GitError
from semantic_platform.authoring.scaffold import InterviewAnswers
from semantic_platform.validate import ShaclValidationReport, SyntaxValidationResult

studio_bp = Blueprint("studio", __name__)

_SH = Namespace("http://www.w3.org/ns/shacl#")
_SEVERITY = {
    str(_SH.Violation): "error",
    str(_SH.Warning): "warning",
    str(_SH.Info): "info",
}


@studio_bp.get("/studio")
def studio_view():
    """Render the modelling studio."""
    model = get_model_config()
    return render_template("studio.html", domains=list_domains(), model=model)


@studio_bp.get("/api/studio/tree")
def api_tree():
    """Return the file tree for the selected domain's content repository."""
    domain_id = request.args.get("domain_id", "")
    return jsonify({"domain_id": domain_id, "files": workspace_tree(domain_id)})


@studio_bp.get("/api/studio/file")
def api_read_file():
    """Return a single file's content from the domain repository.

    Degrades gracefully (200 with an ``error`` note) when the domain/file is
    missing, matching the platform's "every GET route returns 200" contract.
    """
    domain_id = request.args.get("domain_id", "")
    path = request.args.get("path", "")
    if not domain_id or not path:
        return jsonify({"path": path, "content": "", "error": "domain_id and path are required."})
    try:
        return jsonify({"path": path, "content": read_workspace_file(domain_id, path)})
    except (KeyError, GitError) as exc:
        return jsonify({"path": path, "content": "", "error": str(exc)})


@studio_bp.post("/api/studio/file")
def api_write_file():
    """Save edited file content into the domain's authoring branch."""
    payload = request.get_json(silent=True) or {}
    domain_id = payload.get("domain_id", "")
    path = payload.get("path", "")
    try:
        written = write_workspace_file(domain_id, path, payload.get("content", ""))
    except KeyError as exc:
        return jsonify({"error": f"unknown domain: {exc}"}), 404
    return jsonify({"saved": written})


@studio_bp.post("/api/studio/chat")
def api_studio_chat():
    """Run an authoring turn — conversation or, with answers, scaffold+write+validate."""
    payload = request.get_json(silent=True) or {}
    domain_id = payload.get("domain_id")
    answers = payload.get("answers")
    if answers:
        result = authoring_generate(
            domain_id,
            InterviewAnswers(
                domain_label=answers.get("domain_label", "Domain"),
                prefix=answers.get("prefix", "ex"),
                base_namespace=answers.get("base_namespace", "https://example.org/domain#"),
                classes=tuple(answers.get("classes", [])),
                properties=tuple(tuple(p) for p in answers.get("properties", [])),
                include_shapes=answers.get("include_shapes", True),
                include_sample_data=answers.get("include_sample_data", True),
            ),
        )
    else:
        result = authoring_chat(domain_id, payload.get("message", ""), payload.get("history"))
    return jsonify(
        {
            "status": result.status,
            "reply": result.reply,
            "files": list(result.files),
            "branch": result.branch,
            "validation_ok": result.validation_ok,
            "validation_report": result.validation_report,
            "provider": result.provider,
            "model": result.model_id,
        }
    )


@studio_bp.post("/api/studio/pr")
def api_studio_pr():
    """Commit the authoring branch and open (or link) a Pull Request."""
    payload = request.get_json(silent=True) or {}
    domain_id = payload.get("domain_id", "")
    try:
        ref = commit_and_open_pr(domain_id, payload.get("title"), payload.get("body"))
    except KeyError as exc:
        return jsonify({"error": f"unknown domain: {exc}"}), 404
    return jsonify(
        {
            "branch": ref.branch,
            "pushed": ref.pushed,
            "pull_request_url": ref.pull_request_url,
            "compare_url": ref.compare_url,
            "message": ref.message,
        }
    )


@studio_bp.get("/api/studio/status")
def api_studio_status():
    """Return git working-tree status for the selected domain (badges + branch)."""
    domain_id = request.args.get("domain_id", "")
    try:
        status = workspace_status(domain_id)
    except KeyError:
        return jsonify({"branch": "", "clean": True, "files": []})
    return jsonify(
        {
            "branch": status.branch,
            "clean": status.clean,
            "files": [
                {"path": f.path, "code": f.code, "index": f.index, "worktree": f.worktree}
                for f in status.files
            ],
        }
    )


@studio_bp.get("/api/studio/diff")
def api_studio_diff():
    """Return the unified diff for one workspace file."""
    domain_id = request.args.get("domain_id", "")
    path = request.args.get("path", "")
    try:
        return jsonify({"path": path, "diff": workspace_diff(domain_id, path)})
    except (KeyError, GitError) as exc:
        return jsonify({"path": path, "diff": "", "error": str(exc)})


@studio_bp.post("/api/studio/validate")
def api_studio_validate():
    """Validate the selected domain workspace and return a flat problems list."""
    payload = request.get_json(silent=True) or {}
    domain_id = payload.get("domain_id", "")
    try:
        syntax, report = validate_workspace(domain_id)
    except KeyError as exc:
        return jsonify({"error": f"unknown domain: {exc}"}), 404
    problems = _problems_from_validation(syntax, report)
    errors = sum(1 for p in problems if p["severity"] == "error")
    warnings = sum(1 for p in problems if p["severity"] == "warning")
    return jsonify(
        {"ok": not errors, "errors": errors, "warnings": warnings, "problems": problems}
    )


@studio_bp.post("/api/studio/query")
def api_studio_query():
    """Run a SPARQL SELECT against the domain workspace and return tabular rows."""
    payload = request.get_json(silent=True) or {}
    domain_id = payload.get("domain_id", "")
    query_text = payload.get("query", "")
    try:
        rows = query_workspace(domain_id, query_text)
    except KeyError as exc:
        return jsonify({"error": f"unknown domain: {exc}"}), 404
    except Exception as exc:  # noqa: BLE001 - surface any SPARQL parse/eval error inline
        return jsonify({"columns": [], "rows": [], "error": str(exc)})
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    return jsonify({"columns": columns, "rows": rows})


@studio_bp.post("/api/studio/analytics")
def api_studio_analytics():
    """Return graph statistics and analytics for the domain workspace."""
    payload = request.get_json(silent=True) or {}
    domain_id = payload.get("domain_id", "")
    try:
        return jsonify(workspace_analytics(domain_id))
    except KeyError as exc:
        return jsonify({"error": f"unknown domain: {exc}"}), 404


@studio_bp.post("/api/studio/search")
def api_studio_search():
    """Run a semantic search over the domain workspace graph."""
    payload = request.get_json(silent=True) or {}
    domain_id = payload.get("domain_id", "")
    try:
        return jsonify({"results": search_workspace(domain_id, payload.get("query", ""))})
    except KeyError as exc:
        return jsonify({"error": f"unknown domain: {exc}"}), 404


def _workspace_relpath(path: Path) -> str:
    """Render a syntax-result path as a workspace-relative path (for opening files)."""
    parts = path.parts
    if "rdf" in parts:
        return "/".join(parts[parts.index("rdf"):])
    return path.name


def _problems_from_validation(
    syntax: list[SyntaxValidationResult], report: ShaclValidationReport
) -> list[dict]:
    """Flatten syntax errors and SHACL violations into clickable problem rows."""
    problems: list[dict] = []
    for result in syntax:
        if not result.valid:
            problems.append(
                {
                    "severity": "error",
                    "file": _workspace_relpath(result.path),
                    "message": result.message or "RDF syntax error",
                    "kind": "syntax",
                }
            )
    if not report.conforms:
        violations = list(report.report_graph.subjects(RDF.type, _SH.ValidationResult))
        for node in violations:
            message = report.report_graph.value(node, _SH.resultMessage)
            severity = report.report_graph.value(node, _SH.resultSeverity)
            focus = report.report_graph.value(node, _SH.focusNode)
            problems.append(
                {
                    "severity": _SEVERITY.get(str(severity), "error"),
                    "file": str(focus) if focus is not None else "",
                    "message": str(message) if message is not None else "SHACL violation",
                    "kind": "shacl",
                }
            )
        if not violations:
            problems.append(
                {
                    "severity": "error",
                    "file": "",
                    "message": report.report_text.strip() or "SHACL validation failed",
                    "kind": "shacl",
                }
            )
    return problems
