# R2RML mappings

This folder contains domain-neutral R2RML examples for the Semantic Integration Layer.

* `example_person.ttl` demonstrates a logical table, URI template subject map, class assertion, graph assignment, datatype object maps, and a constant IRI object map.
* `example_organization.ttl` demonstrates template-based URI generation and status IRI generation.
* `example_dataset.ttl` demonstrates a SQL query logical table and datatype mappings for dataset metadata.

Mapping files are discovered by both the `.ttl` and `.r2rml` extensions, so a drop-in
`.r2rml` file does not need to be renamed.

The examples follow the W3C R2RML vocabulary (`rr:TriplesMap`, `rr:logicalTable`, `rr:subjectMap`, `rr:predicateObjectMap`, and `rr:objectMap`) while adding Semantic Platform metadata for ownership, version, source dataset, and target graph.

## Drop-in materialization

To add an integration source without writing any code:

1. Drop your ontology/data Turtle file into `rdf/data/` (auto-loaded, syntax-checked,
   and SHACL-validated). Add a matching shape to `rdf/shapes/` for real validation.
2. Drop your R2RML mapping into `mappings/r2rml/` (`.r2rml` or `.ttl`). It must include
   the governance metadata (`map:sourcedFrom`, `map:targetGraph`, `map:version`,
   `gov:hasOwner`, `gov:hasSteward`) in addition to the R2RML structure.
3. Provide the relational source:
   * **Self-contained** (default): drop a self-contained `*.sql` file (schema + data)
     into `mappings/sql/`. No external services required.
   * **Live data platform**: set `SOURCE_DATABASE_URL` to your database; the mapping's
     `rr:logicalTable` query runs against it directly.
4. Run `make materialize` to materialize RDF into `output/` (and push to Fuseki when it
   is reachable), or `make load-fuseki` once Fuseki is up to serve it in the UI under
   **Materialization**. `make materialize` is part of `ci-validate`, so it runs in CI too.
