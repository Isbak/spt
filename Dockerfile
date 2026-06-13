FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000

COPY pyproject.toml README.md ./
COPY src ./src
COPY app ./app
COPY rdf ./rdf
COPY scripts ./scripts

# Install the postgres extra so the bundled per-role warehouses (postgres-business /
# postgres-agents, ADR-0019) work out of the box; core stays SQLite-only otherwise.
RUN python -m pip install --no-cache-dir -e ".[postgres]"

EXPOSE 5000
CMD ["python", "-m", "flask", "--app", "app.app:create_app", "run", "--host", "0.0.0.0", "--port", "5000"]
