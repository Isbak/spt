# SQL integration examples

The SQL examples define generic `source_system`, `person`, `organization`, and `dataset` tables. They are intentionally domain-neutral and can be loaded into SQLite for local tests or PostgreSQL for Docker-based integration testing.

Run the local importer with:

```bash
python -m semantic_platform.import_sql mappings/sql/schema.sql mappings/sql/sample_data.sql
```
