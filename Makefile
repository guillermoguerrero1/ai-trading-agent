# AI Trading Agent Makefile

.PHONY: help install dev-install test lint format clean run-api run-ui run-docker build-docker

# Default target
help:
	@echo "AI Trading Agent - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install       Install production dependencies"
	@echo "  dev-install   Install development dependencies"
	@echo "  test          Run tests"
	@echo "  lint          Run linting"
	@echo "  format        Format code"
	@echo "  clean         Clean build artifacts"
	@echo ""
	@echo "Running:"
	@echo "  run-api       Start the API server"
	@echo "  run-ui        Start the Streamlit UI"
	@echo "  run-docker    Start with Docker Compose"
	@echo ""
	@echo "Docker:"
	@echo "  build-docker  Build Docker image"
	@echo "  push-docker   Push Docker image"

# Installation
install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

# Testing
test:
	python -m pytest tests/ -v --tb=short

test-cov:
	python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# Linting and formatting
lint:
	ruff check app/ ui/ tests/
	mypy app/ ui/

format:
	black app/ ui/ tests/
	ruff check --fix app/ ui/ tests/
	isort app/ ui/ tests/

# Cleaning
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

# Running applications
run-api:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-ui:
	streamlit run ui/dashboard.py --server.port 8501

run-docker:
	docker-compose up --build

# Docker operations
build-docker:
	docker build -t ai-trading-agent .

push-docker:
	docker tag ai-trading-agent:latest your-registry/ai-trading-agent:latest
	docker push your-registry/ai-trading-agent:latest

# Database operations
db-migrate:
	alembic upgrade head

db-reset:
	alembic downgrade base
	alembic upgrade head

# Pre-commit
pre-commit-install:
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Development setup
setup-dev: dev-install pre-commit-install
	@echo "Development environment setup complete!"

# Quick setup (alias for setup-dev)
setup: setup-dev
	@echo "Quick setup complete!"

# Production setup
setup-prod: install
	@echo "Production environment setup complete!"

# Quick start
start: run-api
	@echo "API server started at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"

# Full stack
start-all:
	@echo "Starting full stack..."
	@echo "API: http://localhost:8000"
	@echo "UI: http://localhost:8501"
	@echo "MLflow: http://localhost:5000"
	docker-compose up --build
