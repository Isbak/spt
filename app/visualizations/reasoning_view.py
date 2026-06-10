"""Reasoning and explanation visualization data services."""

from __future__ import annotations

from rdflib.namespace import RDF, RDFS

from semantic_platform.reasoning import REASON, PROV, reasoning_summary, run_reasoning


def reasoning_dashboard_data() -> dict[str, object]:
    """Return rule, inference, consistency, and coverage metrics."""
    summary = reasoning_summary()
    summary["rule_execution_count"] = len(summary["rules_used"])
    summary["inference_volume"] = summary["inferred_count"]
    summary["explanation_coverage"] = (
        round(summary["explanation_count"] / summary["inferred_count"], 4)
        if summary["inferred_count"]
        else 1.0
    )
    return summary


def explanations_data() -> list[dict[str, object]]:
    """Return explainable inference assertions with rule, facts, confidence, and timestamp."""
    run = run_reasoning()
    rows = []
    for inference in sorted(run.reasoning_graph.subjects(RDF.type, REASON.Inference), key=str):
        assertion = run.reasoning_graph.value(inference, REASON.generatedAssertion)
        rule = run.reasoning_graph.value(inference, REASON.usesRule)
        confidence = run.reasoning_graph.value(inference, REASON.hasConfidence)
        timestamp = run.reasoning_graph.value(inference, PROV.generatedAtTime)
        sources = [
            str(source) for source in run.reasoning_graph.objects(inference, REASON.inferredFrom)
        ]
        comment = ""
        explanation = run.reasoning_graph.value(inference, REASON.hasExplanation)
        if explanation is not None:
            comment = str(run.reasoning_graph.value(explanation, RDFS.comment) or "")
        rows.append(
            {
                "assertion": str(assertion),
                "rule": str(rule),
                "source_triples": sources,
                "confidence": str(confidence),
                "timestamp": str(timestamp),
                "comment": comment,
            }
        )
    return rows
