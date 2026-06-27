FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

ARG REQUIREMENTS_FILE=requirements.txt
COPY requirements*.txt .
RUN pip install --no-cache-dir -r "$REQUIREMENTS_FILE"

COPY app ./app

USER appuser

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
