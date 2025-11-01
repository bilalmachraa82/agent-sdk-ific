# FundAI Makefile
# Common development commands

.PHONY: help install dev test lint format clean docker-build docker-up docker-down

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "FundAI Development Commands"
	@echo "==========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# SETUP & INSTALLATION
# ============================================================================

install: ## Install dependencies with Poetry
	poetry install --with dev

install-prod: ## Install production dependencies only
	poetry install --only main

setup: ## Complete project setup (install + pre-commit)
	poetry install --with dev
	poetry run pre-commit install
	@echo "✅ Setup complete! Copy .env.example to .env and configure."

# ============================================================================
# DEVELOPMENT
# ============================================================================

dev: ## Run development server with hot reload
	poetry run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-docker: docker-up ## Start all services with Docker Compose
	@echo "✅ Services running:"
	@echo "   API:      http://localhost:8000"
	@echo "   API Docs: http://localhost:8000/docs"
	@echo "   pgAdmin:  http://localhost:5050 (use --profile admin)"

shell: ## Open Poetry shell
	poetry shell

# ============================================================================
# TESTING
# ============================================================================

test: ## Run all tests
	poetry run pytest

test-verbose: ## Run tests with verbose output
	poetry run pytest -vv

test-cov: ## Run tests with coverage report
	poetry run pytest --cov=agents --cov=api --cov=core --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	poetry run pytest -m unit

test-integration: ## Run integration tests only
	poetry run pytest -m integration

test-watch: ## Run tests in watch mode
	poetry run ptw

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: ## Run linters (ruff)
	poetry run ruff check agents/ api/ core/ tests/

lint-fix: ## Auto-fix linting issues
	poetry run ruff check --fix agents/ api/ core/ tests/

format: ## Format code with Black
	poetry run black agents/ api/ core/ tests/

format-check: ## Check code formatting
	poetry run black --check agents/ api/ core/ tests/

typecheck: ## Run type checking with mypy
	poetry run mypy agents/ api/ core/

quality: format lint typecheck ## Run all quality checks

# ============================================================================
# DOCKER
# ============================================================================

docker-build: ## Build Docker image
	docker build -t fundai:latest .

docker-up: ## Start Docker Compose services
	docker-compose up -d

docker-down: ## Stop Docker Compose services
	docker-compose down

docker-logs: ## View Docker Compose logs
	docker-compose logs -f

docker-ps: ## Show running containers
	docker-compose ps

docker-restart: docker-down docker-up ## Restart all services

# ============================================================================
# DATABASE
# ============================================================================

db-migrate: ## Run database migrations
	poetry run alembic upgrade head

db-rollback: ## Rollback last migration
	poetry run alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys data)
	docker-compose down -v
	docker-compose up -d postgres
	@echo "⚠️  Database reset complete"

# ============================================================================
# CLEANUP
# ============================================================================

clean: ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	@echo "✅ Cleanup complete"

clean-all: clean docker-down ## Deep clean (includes Docker volumes)
	docker-compose down -v
	rm -rf data/uploads/* data/outputs/* data/temp/*

# ============================================================================
# MONITORING
# ============================================================================

logs-api: ## View API logs
	docker-compose logs -f api

logs-celery: ## View Celery logs
	docker-compose logs -f celery-worker

logs-postgres: ## View PostgreSQL logs
	docker-compose logs -f postgres

# ============================================================================
# DEPLOYMENT
# ============================================================================

build-prod: ## Build production image
	docker build -t fundai:production --target runtime .

deploy-check: quality test ## Pre-deployment checks
	@echo "✅ All checks passed - ready to deploy"
