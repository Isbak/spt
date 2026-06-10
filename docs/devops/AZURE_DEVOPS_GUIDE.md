# Azure DevOps Guide

## Pipeline Stages

1. Build
2. Validate
3. Test
4. Package
5. Deploy

## Required Checks

- Python dependency installation
- RDF syntax validation
- SHACL validation
- SPARQL query checks
- R2RML mapping presence
- Unit tests
- Flask smoke test

## Rule

Pipeline failures block deployment.
