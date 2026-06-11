"""Governed advisory API and dashboard routes.

Surfaces the generic advisory/optimization capability: rank candidate options against weighted
criteria and return an explainable, non-executing recommendation. When an ``agent_id`` is
supplied, the request is routed through the governed agent tool so the agent's read permission
is enforced (denial returns HTTP 403) — demonstrating that the dispatcher recommends only and
never executes.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from app.visualizations.advisory_view import advisory_dashboard_data
from semantic_platform.advisory import Criterion
from semantic_platform.agents.registry import AgentRegistry
from semantic_platform.agents.tools import AgentToolRegistry
from semantic_platform.api import advise
from semantic_platform.graph import load_graph

advisory_bp = Blueprint("advisory", __name__)


@advisory_bp.get("/advisory")
def advisory_view():
    """Render the advisory dashboard with an illustrative recommendation."""
    return render_template("advisory.html", advisory=advisory_dashboard_data())


@advisory_bp.post("/api/advisory")
def api_advisory():
    """Return a ranked, explainable recommendation for an objective and criteria.

    Optional ``agent_id`` routes through the governed tool (403 on permission denial). When no
    ``candidate_type`` is supplied, the illustrative sample advisory is returned.
    """
    payload = request.get_json(silent=True) or {}
    objective = payload.get("objective", "Recommend the best option")
    candidate_type = payload.get("candidate_type", "")
    criteria_payload = payload.get("criteria", [])
    agent_id = payload.get("agent_id")

    try:
        if agent_id:
            agent = AgentRegistry().require(agent_id)
            tools = AgentToolRegistry(graph=load_graph())
            result = tools.execute(
                agent,
                "advisory",
                objective=objective,
                candidate_type=candidate_type,
                criteria=criteria_payload,
            )
            return jsonify(result)
        if candidate_type:
            criteria = [
                Criterion(
                    name=item["name"],
                    weight=float(item.get("weight", 1.0)),
                    direction=item.get("direction", "maximize"),
                )
                for item in criteria_payload
            ]
            return jsonify(advise(objective, candidate_type, criteria).as_dict())
        return jsonify(advisory_dashboard_data())
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except KeyError as exc:
        return jsonify({"error": f"unknown agent: {exc}"}), 404
