# ADR-0014: Generic Governed Advisory / Optimization Capability

## Status
Accepted

## Context
Users want the platform to support **planner / dispatcher**-style agents — for example a field
service planner or dispatcher — that can "talk to data", analyse it, optimise, and find
patterns. The capability must stay **domain-neutral** (field service is an example only, like
the existing people/organization sample data) and must not break the platform's deliberate
**non-autonomy** guarantee (ADR-0008, ADR-0011, ADR-0013): agents represent, recommend, and
explain, but never autonomously execute business actions.

Most of the required primitives already existed but were scattered: governed read-only LLM
assist and semantic search ("talk to data"), analytics ("analyse"), inference and rules ("find
patterns"), and non-executing execution plans ("plan"). What was missing was a single, generic
way to turn an objective plus candidate options plus weighted criteria into an explainable,
ranked recommendation.

## Decision
Add a domain-neutral **advisory** layer (`semantic_platform.advisory`):

- `recommend(objective, candidates, criteria)` ranks candidates with a transparent,
  min-max-normalised **weighted sum** (each `Criterion` carries a weight and a maximize/minimize
  direction) and returns an `AdvisoryResult` with a per-criterion score breakdown, a
  human-readable rationale, and a **PROV-O** record attributed to the recommender.
- `candidates_from_graph(candidate_type, criteria)` pulls candidate resources of any type and
  their numeric attributes from the governed graph, so the capability works over any domain.
- **Advisory only:** `AdvisoryResult.ready` is always `False`. Nothing in this module executes a
  business action; the RDF `adv:defaultAdvisoryPolicy` records the constraint
  ("Advisory only; recommendations require human approval before any business action"), mirroring
  the orchestration `executionConstraint`. Carrying out an approved recommendation remains the
  job of the existing approval-gated `execution/executor.py:GovernedExecutor`, invoked by a human.
- Exposed as a governed agent tool `advisory` (read scope `reference`, so the agent's read
  permission is enforced via the same `require_safe_action` path as every other tool), through
  `api.advise`, and via a Flask `/advisory` dashboard plus `POST /api/advisory` (which returns
  **403** when an `agent_id` lacks permission). A new `advisory` Make target is added to the
  single-source-of-truth `ci-validate` list.
- Two **illustrative** agents (`field-service-planner`, `field-service-dispatcher`) are
  registered in `rdf/data/agent_registry.ttl`. They are examples — like the sample instance data
  — composing the generic capabilities; the core code contains no field-service assumptions.

## Consequences
The platform can support planner/dispatcher agents that talk to data, analyse, optimise, and
find patterns, while every governance property holds: permission-checked, explainable,
provenance-recorded, and **non-autonomous**. No prior ADR is reversed and no safety gate is
removed; the advisory layer is fully consistent with ADR-0011 and ADR-0013. Going further to
agent-triggered or fully autonomous dispatch would require a superseding ADR and is explicitly
out of scope here.
