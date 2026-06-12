"""Setup pages: LLM model selection and domain↔git associations."""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from semantic_platform.api import (
    add_domain,
    get_model_config,
    list_domains,
    provider_status,
    remove_domain,
    set_model_config,
    test_model_connection,
)
from semantic_platform.authoring.workspace_config import SUPPORTED_PROVIDERS

setup_bp = Blueprint("setup", __name__)


@setup_bp.get("/setup/models")
def model_setup_view():
    """Render the LLM model setup page."""
    return render_template(
        "model_setup.html",
        config=get_model_config(),
        status=provider_status(),
        providers=SUPPORTED_PROVIDERS,
    )


@setup_bp.post("/api/setup/models")
def api_set_model():
    """Persist the selected provider/model."""
    payload = request.get_json(silent=True) or request.form
    try:
        config = set_model_config(
            payload.get("provider", "local"),
            payload.get("model") or None,
            payload.get("ollama_base_url") or None,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if request.is_json:
        return jsonify(config.__dict__)
    return redirect(url_for("setup.model_setup_view"))


@setup_bp.post("/api/setup/models/test")
def api_test_model():
    """Run a tiny completion to verify the active model is reachable."""
    result = test_model_connection()
    return jsonify(result), (200 if result.get("ok") else 502)


@setup_bp.get("/setup/domains")
def domain_setup_view():
    """Render the domain↔git association page."""
    return render_template("domain_settings.html", domains=list_domains())


@setup_bp.post("/api/setup/domains")
def api_add_domain():
    """Add (or update) a domain reference."""
    payload = request.get_json(silent=True) or request.form
    label = (payload.get("label") or "").strip()
    if not label:
        return jsonify({"error": "A domain label is required."}), 400
    domain = add_domain(
        label,
        payload.get("remote_url", ""),
        payload.get("branch") or "main",
        payload.get("token_env") or None,
    )
    if request.is_json:
        return jsonify(domain.__dict__)
    return redirect(url_for("setup.domain_setup_view"))


@setup_bp.post("/api/setup/domains/<domain_id>/delete")
def api_remove_domain(domain_id: str):
    """Remove a domain reference."""
    removed = remove_domain(domain_id)
    if request.is_json:
        return jsonify({"removed": removed})
    return redirect(url_for("setup.domain_setup_view"))
