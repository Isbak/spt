# ADR-0015: Drop-in Domain Models and Knowledge-Architect Onboarding

## Status
Accepted — the browser **upload/validate** write path was later retired (see *Superseded* below).

## Context
A knowledge architect onboards a new domain by supplying three artefacts: a domain **ontology**
(`owl:Ontology`), a **SHACL shape** file, and an **R2RML mapping**. The platform already
auto-discovers these by location — `graph.load_graph()` re-parses the RDF tree on every request
(no caching), validation globs `rdf/shapes/`, and `r2rdf.mapping_files()` globs `mappings/r2rml/`
— so a dropped ontology already flows into the graph, ontology browser, and search.

What was missing was (a) a view that presents a domain as **one unit** rather than three assets
scattered across the existing split directories, (b) any UI page for SHACL shapes at all, and
(c) a way to add a bundle without filesystem access. The directories must stay split (they are
the configured `Settings` dirs reused by validation, materialization, and reasoning), so the
"domain" must be reconstructed rather than stored.

## Decision
Add a domain-neutral **domain model** layer that groups the split assets by namespace, plus a
shapes catalog, surfaced through the facade and the Flask UI:

- `semantic_platform.shapes.list_shapes()` returns `ShapeRecord`s for the SHACL shapes in
  `settings.shapes_dir` (per-file parse preserves the source filename), powering a new `/shapes`
  page and feeding the grouping.
- `semantic_platform.domain_models.list_domain_models()` treats each `owl:Ontology` as a domain
  and assigns classes, properties, shapes (`sh:targetClass`), and mappings (`rr:class` /
  `rr:predicate`) by **namespace prefix derived from the ontology IRI**. Overlapping namespaces
  resolve to the **most specific (longest) base**; anything matching no declared ontology lands in
  a synthetic **Shared / Core** bucket so nothing is silently dropped.
- `import_domain_files()` is the write path behind a browser upload: it validates every supplied
  file (Turtle syntax, plus the existing `r2rdf.validate_mapping` governance checks for mappings),
  sanitizes filenames against path traversal, and writes **all files or none** so a failed import
  never leaves a partial bundle on disk. It writes only into the configured `ontology_dir`,
  `shapes_dir`, and `r2rml_dir`.
- Exposed through `api.get_domain_models` / `api.list_shape_records` / `api.import_domain`, a
  `domain_models` Flask blueprint (`/domain-models` overview + `POST /domain-models/import`) and a
  `shapes` blueprint (`/shapes`), with nav entries in the Knowledge Graph group. A new
  `domain-models` Make target is added to the single-source-of-truth `ci-validate` list.

## Consequences
Adding a domain is now "drop the three files in (or upload them) and it shows up grouped" — no
manifest edit for the grouping itself. The capability stays **domain-neutral** (grouping is purely
namespace-based; no domain assumptions in core code) and preserves governance: mapping uploads
still enforce the ADR-0004/ADR-0012 governance metadata, and a brand-new `map:targetGraph` still
requires a manual `rdf/graphs/manifest.ttl` entry (surfaced as an informational note, never
auto-edited, per ADR-0007). The upload path was the platform's first UI-driven write to the RDF
tree; it is validate-before-write and confined to the configured asset directories. No prior ADR
is reversed.

## Superseded
The browser **upload & validate** form (`import_domain_files` / `api.import_domain` /
`POST /domain-models/import`) has been removed. Authoring new or edited domain content is now
handled by the governed conversational **Studio** (ADR-0016), which scaffolds and validates RDF
in a sandboxed clone of a separate domain content repo and surfaces it as a human-reviewed Pull
Request — a stronger governance posture than a direct write into the authoritative RDF tree. The
read-only **namespace-grouping** view (`list_domain_models`, `/domain-models`) and the `/shapes`
catalog remain unchanged.
