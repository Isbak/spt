# Ontology Development Guide

## Principles

- Reuse standards before creating custom vocabularies.
- Keep ontology domain-neutral in the platform core.
- Separate core ontology from domain extensions.
- Version ontologies using semantic versioning.
- Validate data with SHACL.

## Standards

- RDF
- RDFS
- OWL
- SHACL
- SKOS
- PROV-O
- Dublin Core
- R2RML

## Versioning

```ttl
owl:versionInfo "1.0.0"
```

Major version: breaking semantic change.  
Minor version: new concepts.  
Patch version: non-breaking fixes.
