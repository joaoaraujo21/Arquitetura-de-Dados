# ─────────────────────────────────────────────
# OpenRouter Data Engineering - Makefile
# ─────────────────────────────────────────────

.PHONY: help install setup dev test lint type-check clean
.PHONY: docker-up docker-down docker-restart
.PHONY: test-unit test-integration test-coverage lint-fix format
.PHONY: pipeline-run pipeline-test
.PHONY: docs-serve docs-build

# ───── Help ─────
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m%-20s\033[0m %s\n", "TARGET", "DESCRIPTION"} /^[a-zA-Z_-]+:.*?##/ {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ───── Install & Setup ─────
install: ## Install project dependencies
	@echo "Installing dependencies..."
	@pip install -e ".[dev,test]" || true
	@echo "✓ Installed."

setup: install docker-up ## Setup project: install deps + start services
	@python -c "from src.settings import Settings; Settings()"
	@echo "✓ Setup complete."

# ───── Development ─────
dev: setup ## Start development environment
	@echo "Starting development services..."
	@echo "Airflow UI: http://localhost:8080"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"
	@echo "pgAdmin: http://localhost:5050"

# ───── Docker ─────
docker-up: ## Start Docker services
	@docker compose up -d
	@echo "✓ Services started."

docker-down: ## Stop Docker services
	@docker compose down -v

docker-restart: docker-down docker-up ## Restart Docker services

# ───── Testing ─────
test: test-unit test-integration ## Run all tests
	@echo "✓ All tests passed."

test-unit: ## Run unit tests
	@echo "Running unit tests..."
	@pytest tests/unit -v --cov=src --cov-report=term-missing

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	@pytest tests/integration -v

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	@pytest tests/ -v --cov=src --cov-report=html --cov-report=xml

# ───── Linting & Formatting ─────
lint: ## Lint code
	@echo "Linting..."
	@ruff check src tests
	@echo "✓ Lint passed."

lint-fix: ## Fix lint issues
	@echo "Fixing lint issues..."
	@ruff check --fix src tests
	@ruff format src tests

format: ## Format code
	@echo "Formatting..."
	@ruff format src tests

type-check: ## Type check with mypy
	@echo "Type checking..."
	@mypy src --strict
	@echo "✓ Type check passed."

# ───── Pipelines ─────
pipeline-run: ## Run example pipeline
	@echo "Running pipeline..."
	@python -m src.pipelines.example_pipeline

pipeline-test: ## Test pipelines
	@echo "Testing pipelines..."
	@pytest tests/unit/test_pipelines.py -v

# ───── Database ─────
db-migrate: ## Run database migrations
	@echo "Running migrations..."
	@alembic upgrade head

db-seed: ## Seed database with sample data
	@echo "Seeding database..."
	@python scripts/seed.py

db-shell: ## Open database shell
	@psql $(DATABASE_URL)

# ───── Documentation ─────
docs-serve: ## Serve documentation locally
	@mkdocs serve

docs-build: ## Build documentation
	@mkdocs build

# ───── Clean ─────
clean: ## Clean up build artifacts
	@echo "Cleaning up..."
	@rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	@rm -rf htmlcov .coverage coverage.xml
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned."

clean-data: ## Clean local data (not versioned)
	@echo "Cleaning local data..."
	@rm -rf data/raw/* data/processed/* data/external/*
	@echo "✓ Data cleaned."

# ───── Pre-commit ─────
pre-commit-install: ## Install pre-commit hooks
	@pre-commit install

pre-commit-run: ## Run pre-commit on all files
	@pre-commit run --all-files

# ───── Release ─────
release: clean test lint type-check ## Build release
	@echo "Building release..."
	@python -m build
	@echo "✓ Release built."