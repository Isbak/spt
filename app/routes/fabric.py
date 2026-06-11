"""Enterprise Knowledge Fabric API and portal routes."""

from __future__ import annotations

from dataclasses import asdict
from flask import Blueprint, jsonify, render_template

from semantic_platform.fabric.catalog import FabricCatalog
from semantic_platform.fabric.context import ContextLayer
from semantic_platform.fabric.lineage import EnterpriseLineage
from semantic_platform.analytics import fabric_metrics

fabric_bp = Blueprint("fabric", __name__)


def _catalog() -> FabricCatalog:
    return FabricCatalog()


def _dicts(rows):
    return [asdict(row) for row in rows]


@fabric_bp.get("/api/domains")
def api_domains():
    return jsonify(_dicts(_catalog().domains.list_domains()))


@fabric_bp.get("/api/products")
def api_products():
    return jsonify(_dicts(_catalog().products.list_products()))


@fabric_bp.get("/api/contracts")
def api_contracts():
    return jsonify(_dicts(_catalog().contracts.list_contracts()))


@fabric_bp.get("/api/glossary")
def api_glossary():
    return jsonify(_dicts(_catalog().glossary.list_terms()))


@fabric_bp.get("/api/fabric")
def api_fabric():
    catalog = _catalog()
    return jsonify({"summary": catalog.summary(), "metrics": fabric_metrics()})


@fabric_bp.get("/api/federation")
def api_federation():
    return jsonify(_dicts(_catalog().federation.list_federations()))


@fabric_bp.get("/knowledge-fabric")
def knowledge_fabric_view():
    catalog = _catalog()
    return render_template("knowledge_fabric.html", summary=catalog.summary(), metrics=fabric_metrics())


@fabric_bp.get("/domains")
def domains_view():
    catalog = _catalog()
    return render_template("domains.html", domains=catalog.domains.list_domains())


@fabric_bp.get("/products")
def products_view():
    catalog = _catalog()
    return render_template("products.html", products=catalog.products.list_products())


@fabric_bp.get("/contracts")
def contracts_view():
    catalog = _catalog()
    return render_template("contracts.html", contracts=catalog.contracts.list_contracts())


@fabric_bp.get("/glossary")
def glossary_view():
    catalog = _catalog()
    return render_template("glossary.html", terms=catalog.glossary.list_terms())


@fabric_bp.get("/federation")
def federation_view():
    catalog = _catalog()
    return render_template("federation.html", federations=catalog.federation.list_federations())


@fabric_bp.get("/interoperability")
def interoperability_view():
    catalog = _catalog()
    return render_template(
        "interoperability.html",
        mappings=catalog.interoperability.list_mappings(),
        score=catalog.interoperability.interoperability_score(),
        contexts=ContextLayer().list_contexts(),
        lineage=EnterpriseLineage().edges(),
    )
