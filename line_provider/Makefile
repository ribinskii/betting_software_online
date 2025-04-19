# Makefile for test commands

COMPOSE_FILE := tests/docker-compose-test.yml

.PHONY: test-infra test-stop test-run test

# Start test infrastructure
test-infra:
	docker compose -f $(COMPOSE_FILE) up -d && sleep 5

# Stop test infrastructure
test-stop:
	docker compose -f $(COMPOSE_FILE) down

# Run tests
test-run:
	poetry run pytest -s tests

# Full test sequence: start infra, run tests, stop infra
test: test-infra test-run