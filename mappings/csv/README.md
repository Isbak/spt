# CSV integration examples

CSV files provide realistic, domain-neutral samples that map to core ontology concepts:

* `people.csv` maps rows to `sp:Entity` resources with names, identifiers, email values, and organization links.
* `organizations.csv` maps rows to `sp:Entity` resources for organizations.
* `datasets.csv` maps rows to `sp:Dataset` resources with versions and statuses.

Run the importer with:

```bash
python -m semantic_platform.import_csv mappings/csv/people.csv
```
