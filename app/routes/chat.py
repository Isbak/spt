"""Global, context-aware chat panel backend.

Two modes, both governed:

* **ask** (default) — a read-only question about the data behind the page the user is
  viewing. Routed through the governed assist (``explain_with_agent``), scoped to the
  view's data scope; returns 403 when the assist agent may not read that scope.
* **model** — enters the governed authoring conversation for a selected domain; if no
  domain is configured it returns a prompt pointing at the domain settings page.
"""

from __future__ import annotations

import os

from flask import Blueprint, jsonify, request

from semantic_platform.api import authoring_chat, explain_with_agent, list_domains

chat_bp = Blueprint("chat", __name__)

#: Approved agent used for the read-only "ask about this view" assist.
DEFAULT_CHAT_AGENT = os.getenv("CHAT_AGENT_ID", "semantic-context-agent")


@chat_bp.post("/api/chat")
def api_chat():
    """Answer a chat message in 'ask' (read-only) or 'model' (authoring) mode."""
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    mode = payload.get("mode", "ask")
    context = payload.get("context") or {}
    if not message:
        return jsonify({"error": "Empty message."}), 400

    if mode == "model":
        result = authoring_chat(payload.get("domain_id"), message, payload.get("history"))
        return jsonify(
            {
                "mode": "model",
                "status": result.status,
                "reply": result.reply,
                "domain_id": result.domain_id,
                "provider": result.provider,
                "model": result.model_id,
            }
        )

    scope = context.get("scope", "reference")
    agent_id = payload.get("agent_id") or DEFAULT_CHAT_AGENT
    try:
        result = explain_with_agent(agent_id, scope, message)
    except PermissionError as exc:
        return jsonify({"error": str(exc), "scope": scope}), 403
    except KeyError as exc:
        return jsonify({"error": f"unknown agent: {exc}"}), 404
    return jsonify(
        {
            "mode": "ask",
            "reply": result.text,
            "scope": result.scope,
            "provider": result.provider,
            "model": result.model_id,
            "fact_count": result.fact_count,
        }
    )


@chat_bp.get("/api/chat/domains")
def api_chat_domains():
    """List configured domains for the authoring-mode selector."""
    return jsonify([{"id": d.domain_id, "label": d.label} for d in list_domains()])
