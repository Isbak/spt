"""Enterprise Knowledge Fabric package."""

from semantic_platform.fabric.catalog import FabricCatalog
from semantic_platform.fabric.contracts import ContractRegistry, SemanticContract
from semantic_platform.fabric.domains import DomainRegistry, KnowledgeDomain
from semantic_platform.fabric.federation import FederationRegistry, FederatedGraph
from semantic_platform.fabric.products import KnowledgeProduct, KnowledgeProductCatalog

__all__ = [
    "ContractRegistry",
    "DomainRegistry",
    "FabricCatalog",
    "FederatedGraph",
    "FederationRegistry",
    "KnowledgeDomain",
    "KnowledgeProduct",
    "KnowledgeProductCatalog",
    "SemanticContract",
]
