"""Knowledge-modelling studio: folder tree, editor, and the authoring conversation."""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from semantic_platform.api import (
    authoring_chat,
    authoring_generate,
    commit_and_open_pr,
    list_domains,
    read_workspace_file,
    workspace_tree,
    write_workspace_file,
)
from semantic_platform.authoring.gitrepo import GitError
from semantic_platform.authoring.scaffold import InterviewAnswers

studio_bp = Blueprint("studio", __name__)


@studio_bp.get("/studio")
def studio_view():
    """Render the modelling studio."""
    return render_template("studio.html", domains=list_domains())


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
