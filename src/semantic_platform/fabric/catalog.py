"""Unified Enterprise Knowledge Fabric catalog."""

from __future__ import annotations

from semantic_platform.config import Settings, load_settings
from semantic_platform.fabric.contracts import ContractRegistry
from semantic_platform.fabric.domains import DomainRegistry
from semantic_platform.fabric.federation import FederationRegistry
from semantic_platform.fabric.glossary import Glossary
from semantic_platform.fabric.interoperability import InteroperabilityLayer
from semantic_platform.fabric.products import KnowledgeProductCatalog


class FabricCatalog:
    """Facade for discovering all enterprise semantic assets."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.domains = DomainRegistry(settings=self.settings)
        self.products = KnowledgeProductCatalog(settings=self.settings)
        self.contracts = ContractRegistry(settings=self.settings)
        self.glossary = Glossary(settings=self.settings)
        self.federation = FederationRegistry(settings=self.settings)
        self.interoperability = InteroperabilityLayer(settings=self.settings)

    def summary(self) -> dict[str, int | float]:
        return {
            "domain_count": len(self.domains.list_domains()),
            "product_count": len(self.products.list_products()),
            "contract_count": len(self.contracts.list_contracts()),
            "glossary_term_count": len(self.glossary.list_terms()),
            "federation_count": len(self.federation.list_federations()),
            "interoperability_score": self.interoperability.interoperability_score(),
        }
