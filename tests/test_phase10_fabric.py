from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from app.app import create_app
from semantic_platform.analytics import fabric_metrics
from semantic_platform.fabric.common import CONTRACT, EX
from semantic_platform.fabric.contracts import ContractRegistry
from semantic_platform.fabric.context import ContextLayer
from semantic_platform.fabric.domains import DomainRegistry
from semantic_platform.fabric.federation import FederationRegistry
from semantic_platform.fabric.glossary import Glossary
from semantic_platform.fabric.interoperability import InteroperabilityLayer
from semantic_platform.fabric.products import KnowledgeProductCatalog
from semantic_platform.governance import enterprise_governance_summary


def test_domain_registration_and_ownership():
    registry = DomainRegistry()
    domains = registry.list_domains()
    assert len(domains) >= 3
    assert all(domain.owner for domain in domains)
    assert all(domain.steward for domain in domains)
    assert registry.validate_ownership() == []


def test_product_lifecycle_and_dependencies():
    catalog = KnowledgeProductCatalog()
    products = catalog.list_products()
    assert len(products) >= 3
    assert any(product.lifecycle_state == "Active" for product in products)
    assert "Knowledge Product B" in catalog.dependencies_for("knowledge-product-a")


def test_contract_validation_and_compatibility():
    registry = ContractRegistry()
    assert len(registry.list_contracts()) >= 3
    assert registry.validate_contracts() == []
    assert registry.compatibility_coverage() == 1.0


def test_federation_graph_discovery():
    registry = FederationRegistry()
    federations = registry.list_federations()
    assert federations
    assert registry.federated_graph_count() >= 3
    assert registry.discover_for_domain("Domain A")


def test_glossary_term_management():
    glossary = Glossary()
    terms = glossary.list_terms()
    assert len(terms) >= 2
    assert not glossary.validate_terms()
    assert any("Concept A" in term.synonyms for term in terms)


def test_interoperability_mapping_validation_and_alignment():
    layer = InteroperabilityLayer()
    assert layer.list_mappings()
    assert layer.validate_mappings() == []
    assert layer.validate_contracts() == []
    assert layer.interoperability_score() == 1.0


def test_context_layer_supports_enterprise_contexts():
    contexts = ContextLayer().list_contexts()
    assert {context.context_type for context in contexts} >= {
        "organizational",
        "operational",
        "semantic",
        "execution",
        "agent",
    }


def test_fabric_metrics_and_governance():
    metrics = fabric_metrics()
    assert metrics["domain_count"] >= 3
    assert metrics["product_count"] >= 3
    assert metrics["compatibility_coverage"] == 1.0
    governance = enterprise_governance_summary()
    assert all(count >= 1 for count in governance.values())


def test_register_product_and_contract_on_in_memory_graph():
    graph = Graph()
    product = KnowledgeProductCatalog(graph=graph).register_product("Runtime Product", owner="Owner")
    contract = ContractRegistry(graph=graph).register_contract(
        "Runtime Contract", producer=product.uri, consumer="Runtime Consumer"
    )
    assert product.lifecycle_state == "Active"
    assert contract.compatibility == "Compatible"


def test_contract_validator_reports_missing_fields():
    graph = Graph()
    contract = URIRef(EX["contract-incomplete"])
    graph.add((contract, RDF.type, CONTRACT.SemanticContract))
    graph.add((contract, RDFS.label, Literal("Incomplete")))
    errors = ContractRegistry(graph=graph).validate_contracts()
    assert any("producer" in error for error in errors)
    assert any("compatibility" in error for error in errors)


def test_enterprise_catalog_api_endpoints():
    client = create_app().test_client()
    for path in [
        "/api/domains",
        "/api/products",
        "/api/contracts",
        "/api/glossary",
        "/api/fabric",
        "/api/federation",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert response.get_json() is not None


def test_enterprise_portal_pages_render():
    client = create_app().test_client()
    for path in [
        "/knowledge-fabric",
        "/domains",
        "/products",
        "/contracts",
        "/glossary",
        "/federation",
        "/interoperability",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert b"<h2" in response.data
