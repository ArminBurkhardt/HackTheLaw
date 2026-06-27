.PHONY: dev test test-live neo4j agents index-cellar secv-eval install

install:
	pip install -e ".[dev]"

dev:
	uvicorn server.app:app --reload --port 8000

test:
	pytest tests/ -v -m "not live"

test-live:
	pytest tests/ -v -m live

neo4j:
	docker compose up neo4j -d

agents:
	python -m crucible.runner

index-cellar:
	python -m crucible.grounding.cellar.ingest --scenario=$(SCENARIO)

secv-eval:
	python -m crucible.verify.eval
