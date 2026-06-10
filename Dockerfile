FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.app:create_app

COPY pyproject.toml README.md ./
COPY src ./src
COPY app ./app

RUN pip install --no-cache-dir -e .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.app:create_app()"]
