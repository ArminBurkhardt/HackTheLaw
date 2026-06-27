SERVER_IMAGE ?= hackthelaw-crucible-api
SERVER_PORT ?= 8000
SERVER_REQUIREMENTS ?= requirements.txt
WEB_PORT ?= 3001

.PHONY: test-web test-server dev-server dev-web docker-build-server docker-build-server-adk docker-run-server docker-smoke-server

test-web:
	@if test -d web; then \
		cd web && npm test && npm run lint && ./node_modules/.bin/tsc --noEmit --incremental false && npm run build; \
	else \
		echo "No web/ app in this branch."; \
	fi

test-server:
	PYTHONPATH=server .venv/bin/pytest server/tests

dev-server:
	PYTHONPATH=server .venv/bin/uvicorn app.main:app --reload --app-dir server --port 8000

dev-web:
	@if test -d web; then \
		cd web && CRUCIBLE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --port $(WEB_PORT); \
	else \
		echo "No web/ app in this branch."; \
		exit 1; \
	fi

docker-build-server:
	docker build --build-arg REQUIREMENTS_FILE=$(SERVER_REQUIREMENTS) -t $(SERVER_IMAGE) ./server

docker-build-server-adk:
	$(MAKE) docker-build-server SERVER_REQUIREMENTS=requirements-adk.txt

docker-run-server: docker-build-server
	docker run --rm -p $(SERVER_PORT):8080 -e PORT=8080 $(SERVER_IMAGE)

docker-smoke-server: docker-build-server
	@container="$$(docker run --rm -d -p $(SERVER_PORT):8080 -e PORT=8080 $(SERVER_IMAGE))"; \
	trap 'docker rm -f "$$container" >/dev/null 2>&1' EXIT; \
	for attempt in 1 2 3 4 5; do \
		if curl -fsS "http://127.0.0.1:$(SERVER_PORT)/health"; then exit 0; fi; \
		sleep 1; \
	done; \
	docker logs "$$container"; \
	exit 1
