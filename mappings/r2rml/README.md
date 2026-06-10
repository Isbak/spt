# R2RML mappings

This folder contains domain-neutral R2RML examples for the Semantic Integration Layer.

* `example_person.ttl` demonstrates a logical table, URI template subject map, class assertion, graph assignment, datatype object maps, and a constant IRI object map.
* `example_organization.ttl` demonstrates template-based URI generation and status IRI generation.
* `example_dataset.ttl` demonstrates a SQL query logical table and datatype mappings for dataset metadata.

The examples follow the W3C R2RML vocabulary (`rr:TriplesMap`, `rr:logicalTable`, `rr:subjectMap`, `rr:predicateObjectMap`, and `rr:objectMap`) while adding Semantic Platform metadata for ownership, version, source dataset, and target graph.
