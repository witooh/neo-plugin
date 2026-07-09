SHELL := /usr/bin/env bash

## ============================================================================
## Variables
## ============================================================================

PG_USER     ?= postgres
PG_PASSWORD ?= password
PG_HOST     ?= localhost
PG_PORT     ?= 5432
PG_DATABASE ?= sit_core
PG_SSLMODE  ?= disable
PG_SCHEMA   ?= neoschema
PG_CONNECTION_URL = postgres://$(PG_USER):$(PG_PASSWORD)@$(PG_HOST):$(PG_PORT)/$(PG_DATABASE)?sslmode=$(PG_SSLMODE)&search_path=$(PG_SCHEMA)

MIGRATION_PATH ?= ../../internal/adapters/repository/postgres/migrations
MIGRATION_CMD  ?= cd tools/golang-migrate; go run -tags 'postgres' github.com/golang-migrate/migrate/v4/cmd/migrate

PG_CONTAINER ?= postgres

.PHONY: vendor run-api dev \
        gen db-gen mock-gen \
        test test-short test-cover test-e2e test-unit-e2e \
        create-migration migration-up migration-down \
        pre-build compose-up compose-down \
        tidy tidy-sqlc tidy-golang-migrate tidy-golangci-lint tidy-mockery tidy-govulncheck \
        vulncheck

## ============================================================================
## Application
## ============================================================================

vendor:
	@go mod vendor

run-api:
	@go run ./cmd/api | (trap '' SIGINT; jq); exit 0

dev: run-api

## ============================================================================
## Code generation
## ============================================================================

gen: db-gen mock-gen

db-gen:
	@find . -type d -name "sqlc" -not -path "./tools/*" -exec rm -rf {} +
	@go tool -modfile=tools/sqlc/go.mod sqlc generate

mock-gen:
	@find . -type d -name '*mocks' -exec rm -rf {} +
	@go tool -modfile=tools/mockery/go.mod mockery

## ============================================================================
## Test
## ============================================================================

test:
	@go test -race -v -count=1 ./...

test-short:
	@go test -race -v -count=1 -short ./...

# Run unit tests (-short) with coverage, then print the per-function coverage table.
test-cover:
	@go test -short ./... -coverprofile=cover.profile
	@go tool cover -func cover.profile

# Requires the service to be running (make compose-up) and migrations applied
# (make migration-up). Global setup cleans + seeds the DB on its own.
# Auto-installs tests/e2e/node_modules on first run.
test-e2e:
	@if ! curl -sf http://localhost:8080/health > /dev/null 2>&1; then \
		echo "⏳ Service not running — starting compose..."; \
		$(MAKE) compose-up; \
		echo "⏳ Waiting for service to be healthy..."; \
		for i in $$(seq 1 30); do \
			curl -sf http://localhost:8080/health > /dev/null 2>&1 && break; \
			sleep 2; \
		done; \
	fi
	@echo "🧪 Running E2E tests..."
	@cd tests/e2e && npm install --silent && npm test

test-e2e-coverage: ## Run E2E tests with coverage report
	@echo "Running E2E tests with coverage..."
	@cd tests/e2e && npm install && npm run test:coverage

test-e2e-watch: ## Run E2E tests in watch mode
	@echo "Running E2E tests in watch mode..."
	@cd tests/e2e && npm install && npm run test:watch
	
test-e2e-debug: ## Run E2E tests in debug mode
	@echo "Running E2E tests in debug mode..."
	@cd tests/e2e && npm install && npm run test:debug

# Run Go unit tests first, then the TypeScript E2E suite.
test-unit-e2e: test test-e2e

## ============================================================================
## Database — migrations & seed
## ============================================================================

# Usage: make create-migration NAME=example
create-migration:
	@go tool -modfile=tools/golang-migrate/go.mod migrate create -ext sql -dir internal/adapters/repository/postgres/migrations -seq $(NAME)

migration-up:
	@if ls internal/adapters/repository/postgres/migrations/*.sql >/dev/null 2>&1; then \
		$(MIGRATION_CMD) -path $(MIGRATION_PATH) -database "$(PG_CONNECTION_URL)" up; \
	else \
		echo "no migrations yet — skipping (neo adds them under internal/adapters/repository/postgres/migrations)"; \
	fi

migration-down:
	@$(MIGRATION_CMD) -path $(MIGRATION_PATH) -database "$(PG_CONNECTION_URL)" down -all

## ============================================================================
## Docker Compose
## ============================================================================

pre-build:
	@rm -rf vendor
	@$(MAKE) db-gen
	@go mod vendor
	@export DOCKER_BUILDKIT=1

compose-up:
	@$(MAKE) pre-build
	@export COMPOSE_DOCKER_CLI_BUILD=1
	@docker compose up -d --build
	@rm -rf vendor
	@$(MAKE) migration-up

compose-down:
	@docker compose down --remove-orphans --volumes

## ============================================================================
## Quality — vuln + tidy
## ============================================================================

vulncheck:
	@go tool -modfile=tools/govulncheck/go.mod govulncheck ./...

tidy: tidy-sqlc tidy-golang-migrate tidy-golangci-lint tidy-mockery tidy-govulncheck
	@go mod tidy

tidy-sqlc:
	@cd tools/sqlc; go mod tidy

tidy-golang-migrate:
	@cd tools/golang-migrate; go mod tidy

tidy-golangci-lint:
	@cd tools/golangci-lint; go mod tidy

tidy-mockery:
	@cd tools/mockery; go mod tidy

tidy-govulncheck:
	@cd tools/govulncheck; go mod tidy
