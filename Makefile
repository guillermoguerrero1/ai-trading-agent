# AI Trading Agent Makefile

.PHONY: help install dev-install test lint format clean run-api run-ui run-dev run-prod run-docker build-docker dataset train cleanup-ports db-clean reset health routes open-trading test-order test-logs model-status migrate revision backtest full-check logs-api logs-ui smoke nq-backfill nq-dataset nq-train nq-all

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
	@echo "  run-api       Start the API server (default config)"
	@echo "  run-ui        Start the Streamlit UI"
	@echo "  run-dev       Start API server with development config (.env.dev)"
	@echo "  run-prod      Start API server with production config (.env.prod)"
	@echo "  run-docker    Start with Docker Compose"
	@echo ""
	@echo "API Testing:"
	@echo "  health        Check API health status"
	@echo "  routes        List all API routes"
	@echo "  smoke         Run smoke tests (open-trading + test-order + test-logs)"
	@echo "  open-trading  Open trading hours for smoke testing"
	@echo "  test-order    Test paper order placement and fill"
	@echo "  test-logs     Regression test for trade logs endpoints"
	@echo "  full-check    Complete system check (reset -> health -> routes -> smoke -> dataset -> train -> model-status)"
	@echo ""
	@echo "Maintenance:"
	@echo "  cleanup-ports Kill processes on ports 9001, 9012, 9014"
	@echo "  db-clean      Stop servers and reset database (preserves backups)"
	@echo "  reset         Complete system reset (stop, clean, restart)"
	@echo ""
	@echo "Data:"
	@echo "  dataset       Build dataset from trade logs"
	@echo "  train         Train baseline model"
	@echo "  model-status  Check model status and metrics"
	@echo ""
	@echo "NQ Futures:"
	@echo "  nq-backfill   Generate NQ breakout trades from CSV data"
	@echo "  nq-dataset    Build dataset from NQ trades (exclude seed data)"
	@echo "  nq-train      Train model on NQ dataset"
	@echo "  nq-all        Complete NQ pipeline (backfill + dataset + train)"
	@echo ""
	@echo "Database:"
	@echo "  migrate       Run database migrations (upgrade head)"
	@echo "  revision      Create new migration (autogenerate)"
	@echo ""
	@echo "Backtesting:"
	@echo "  backtest      Run backtesting simulation (requires data file)"
	@echo ""
	@echo "Logging:"
	@echo "  logs-api      Tail API server logs"
	@echo "  logs-ui       Tail Streamlit UI logs"
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
	uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload

run-ui:
	streamlit run ui/dashboard.py --server.port 8501

run-dev:
	@echo "Starting API server with development configuration..."
	@if [ -f ".env.dev" ]; then \
		cp .env.dev .env && \
		uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload; \
	else \
		echo "Error: .env.dev file not found"; \
		exit 1; \
	fi

run-prod:
	@echo "Starting API server with production configuration..."
	@if [ -f ".env.prod" ]; then \
		cp .env.prod .env && \
		uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4; \
	else \
		echo "Error: .env.prod file not found"; \
		exit 1; \
	fi

run-docker:
	docker-compose up --build

# API testing
health:
	@echo "Checking API health status..."
	@if command -v curl >/dev/null 2>&1; then \
		if command -v jq >/dev/null 2>&1; then \
			curl -s http://localhost:9001/v1/health | jq .; \
		else \
			curl -s http://localhost:9001/v1/health; \
		fi; \
	else \
		echo "Error: curl not found. Please install curl to use this target."; \
		exit 1; \
	fi

routes:
	@echo "Listing all API routes..."
	@if command -v curl >/dev/null 2>&1; then \
		if command -v jq >/dev/null 2>&1; then \
			curl -s http://localhost:9001/v1/debug/routes | jq .; \
		else \
			curl -s http://localhost:9001/v1/debug/routes; \
		fi; \
	else \
		echo "Error: curl not found. Please install curl to use this target."; \
		exit 1; \
	fi

# Open trading hours for smoke testing
open-trading:
	@echo "Opening trading hours for smoke testing..."
	@if [ -f "scripts/open_trading_hours.sh" ]; then \
		chmod +x scripts/open_trading_hours.sh && \
		./scripts/open_trading_hours.sh; \
	elif [ -f "scripts/open_trading_hours.ps1" ]; then \
		powershell -ExecutionPolicy Bypass -File scripts/open_trading_hours.ps1; \
	else \
		echo "Error: No open trading hours script found. Please ensure scripts/open_trading_hours.sh or scripts/open_trading_hours.ps1 exists."; \
		exit 1; \
	fi

# Test paper order placement and fill
test-order:
	@echo "Testing paper order placement and fill simulation..."
	@if [ -f "scripts/test_paper_order.py" ]; then \
		python3 scripts/test_paper_order.py; \
	elif [ -f "scripts/test_paper_order.sh" ]; then \
		chmod +x scripts/test_paper_order.sh && \
		./scripts/test_paper_order.sh; \
	else \
		echo "Error: No test order script found. Please ensure scripts/test_paper_order.py or scripts/test_paper_order.sh exists."; \
		exit 1; \
	fi

# Regression test for trade logs endpoints
test-logs:
	@echo "Running regression test for trade logs endpoints..."
	@if [ -f "scripts/test_trade_logs.py" ]; then \
		python3 scripts/test_trade_logs.py; \
	elif [ -f "scripts/test_trade_logs.sh" ]; then \
		chmod +x scripts/test_trade_logs.sh && \
		./scripts/test_trade_logs.sh; \
	else \
		echo "Error: No trade logs test script found. Please ensure scripts/test_trade_logs.py or scripts/test_trade_logs.sh exists."; \
		exit 1; \
	fi

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

db-clean:
	@echo "Stopping servers and cleaning database..."
	@echo "Stopping uvicorn processes on port 9001..."
	@if command -v lsof >/dev/null 2>&1; then \
		PIDS=$$(lsof -ti:9001 2>/dev/null || true); \
		if [ -n "$$PIDS" ]; then \
			echo "Found uvicorn processes: $$PIDS"; \
			echo "$$PIDS" | xargs kill -TERM 2>/dev/null || true; \
			sleep 2; \
			echo "$$PIDS" | xargs kill -9 2>/dev/null || true; \
		fi; \
	elif command -v netstat >/dev/null 2>&1; then \
		PIDS=$$(netstat -ano 2>/dev/null | grep ":9001.*LISTENING" | awk '{print $$NF}' | grep -E '^[0-9]+$$' || true); \
		if [ -n "$$PIDS" ]; then \
			echo "Found processes on port 9001: $$PIDS"; \
			echo "$$PIDS" | xargs kill -TERM 2>/dev/null || true; \
			sleep 2; \
			echo "$$PIDS" | xargs kill -9 2>/dev/null || true; \
		fi; \
	fi
	@echo "Stopping Docker containers..."
	@if command -v docker >/dev/null 2>&1; then \
		CONTAINERS=$$(docker ps --format "{{.ID}}" --filter "publish=9001" 2>/dev/null || true); \
		if [ -n "$$CONTAINERS" ]; then \
			echo "Stopping Docker containers: $$CONTAINERS"; \
			echo "$$CONTAINERS" | xargs docker stop 2>/dev/null || true; \
		fi; \
	fi
	@echo "Removing database file..."
	@if [ -f "trading_agent.db" ]; then \
		rm -f trading_agent.db; \
		echo "✓ Database deleted: trading_agent.db"; \
	else \
		echo "ℹ No database file found"; \
	fi
	@echo "Preserving backups..."
	@if ls trading_agent.db.bak* >/dev/null 2>&1; then \
		echo "✓ Backups preserved: $$(ls trading_agent.db.bak* | wc -l) backup files"; \
	else \
		echo "ℹ No backup files found"; \
	fi
	@echo ""
	@echo "Database reset. Schema will be recreated on next startup."

# Complete system reset
reset:
	@echo "=== Complete System Reset ==="
	@echo "This will stop all processes, clean the database, and restart the system."
	@echo ""
	@echo "Step 1: Stopping all processes..."
	@echo "Stopping uvicorn processes on port 9001..."
	@if command -v lsof >/dev/null 2>&1; then \
		PIDS=$$(lsof -ti:9001 2>/dev/null || true); \
		if [ -n "$$PIDS" ]; then \
			echo "Found uvicorn processes: $$PIDS"; \
			echo "$$PIDS" | xargs kill -TERM 2>/dev/null || true; \
			sleep 2; \
			echo "$$PIDS" | xargs kill -9 2>/dev/null || true; \
		fi; \
	elif command -v netstat >/dev/null 2>&1; then \
		PIDS=$$(netstat -ano 2>/dev/null | grep ":9001.*LISTENING" | awk '{print $$NF}' | grep -E '^[0-9]+$$' || true); \
		if [ -n "$$PIDS" ]; then \
			echo "Found processes on port 9001: $$PIDS"; \
			echo "$$PIDS" | xargs kill -TERM 2>/dev/null || true; \
			sleep 2; \
			echo "$$PIDS" | xargs kill -9 2>/dev/null || true; \
		fi; \
	fi
	@echo "Stopping Docker containers..."
	@if command -v docker >/dev/null 2>&1; then \
		CONTAINERS=$$(docker ps --format "{{.ID}}" --filter "publish=9001" 2>/dev/null || true); \
		if [ -n "$$CONTAINERS" ]; then \
			echo "Stopping Docker containers: $$CONTAINERS"; \
			echo "$$CONTAINERS" | xargs docker stop 2>/dev/null || true; \
		fi; \
		# Also stop any containers with our service names
		CONTAINERS=$$(docker ps --format "{{.Names}}" --filter "name=ai-trading-agent" 2>/dev/null || true); \
		if [ -n "$$CONTAINERS" ]; then \
			echo "Stopping trading agent containers: $$CONTAINERS"; \
			echo "$$CONTAINERS" | xargs docker stop 2>/dev/null || true; \
		fi; \
	fi
	@echo ""
	@echo "Step 2: Cleaning database..."
	@if [ -f "trading_agent.db" ]; then \
		rm -f trading_agent.db; \
		echo "✓ Database deleted: trading_agent.db"; \
	else \
		echo "ℹ No database file found"; \
	fi
	@echo "Preserving backups..."
	@if ls trading_agent.db.bak* >/dev/null 2>&1; then \
		echo "✓ Backups preserved: $$(ls trading_agent.db.bak* | wc -l) backup files"; \
	else \
		echo "ℹ No backup files found"; \
	fi
	@echo ""
	@echo "Step 3: Determining restart method..."
	@if command -v docker >/dev/null 2>&1 && [ -f "docker-compose.yml" ]; then \
		echo "Docker detected. Rebuilding and starting containers..."; \
		echo ""; \
		docker-compose down --remove-orphans 2>/dev/null || true; \
		docker-compose build --no-cache; \
		docker-compose up -d; \
		echo ""; \
		echo "✓ System reset complete!"; \
		echo "API: http://localhost:9001"; \
		echo "UI: http://localhost:8501"; \
		echo "MLflow: http://localhost:5000"; \
		echo ""; \
		echo "Database schema will be recreated on first API request."; \
	else \
		echo "Docker not available. Starting local development server..."; \
		echo ""; \
		echo "Starting API server on port 9001..."; \
		echo "Press Ctrl+C to stop the server"; \
		echo ""; \
		uvicorn app.main:app --host 0.0.0.0 --port 9001 --reload; \
	fi

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
	@echo "API server started at http://localhost:9001"
	@echo "API docs at http://localhost:9001/docs"

# Dataset operations
dataset:
	python -m engines.supervised.build_dataset

# Training operations
train:
	python engines/supervised/train.py

# Model status check
model-status:
	@echo "Checking model status and metrics..."
	@if command -v curl >/dev/null 2>&1; then \
		HTTP_CODE=$$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9001/v1/model/status); \
		if [ "$$HTTP_CODE" = "200" ]; then \
			if command -v jq >/dev/null 2>&1; then \
				curl -s http://localhost:9001/v1/model/status | jq .; \
			else \
				curl -s http://localhost:9001/v1/model/status; \
			fi; \
		elif [ "$$HTTP_CODE" = "404" ]; then \
			echo "Model status endpoint not available (404). The model router may not be registered."; \
			echo "Available model files:"; \
			ls -la models/ 2>/dev/null || echo "No models directory found"; \
			echo ""; \
			echo "To enable model status endpoint, ensure the model router is properly registered in app/main.py"; \
		else \
			echo "Model status endpoint returned HTTP $$HTTP_CODE"; \
			curl -s http://localhost:9001/v1/model/status; \
		fi; \
	else \
		echo "Error: curl not found. Please install curl to use this target."; \
		exit 1; \
	fi

# Database migrations
migrate:
	@echo "Running database migrations..."
	alembic upgrade head

revision:
	@echo "Creating new migration..."
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

# Port cleanup
cleanup-ports:
	@echo "Cleaning up processes on ports 9001, 9012, 9014..."
	@if [ -f "scripts/cleanup_ports.sh" ]; then \
		chmod +x scripts/cleanup_ports.sh && \
		./scripts/cleanup_ports.sh; \
	elif [ -f "scripts/cleanup_ports.ps1" ]; then \
		powershell -ExecutionPolicy Bypass -File scripts/cleanup_ports.ps1; \
	else \
		echo "Error: No cleanup script found. Please ensure scripts/cleanup_ports.sh or scripts/cleanup_ports.ps1 exists."; \
		exit 1; \
	fi

# Backtesting
backtest:
	@echo "Running backtesting simulation..."
	@if [ -z "$(DATA_FILE)" ]; then \
		echo "Error: DATA_FILE not specified. Usage: make backtest DATA_FILE=path/to/data.csv"; \
		echo "Example: make backtest DATA_FILE=data/sample_btc_data.csv"; \
		exit 1; \
	fi
	@if [ ! -f "$(DATA_FILE)" ]; then \
		echo "Error: Data file not found: $(DATA_FILE)"; \
		exit 1; \
	fi
	python engines/backtest/run.py $(DATA_FILE) \
		--initial-capital $(or $(CAPITAL),10000) \
		--position-size $(or $(POSITION_SIZE),0.1) \
		--stop-loss $(or $(STOP_LOSS),0.02) \
		--take-profit $(or $(TAKE_PROFIT),0.04) \
		--output-dir $(or $(OUTPUT_DIR),reports/backtests)

# Full stack
start-all:
	@echo "Starting full stack..."
	@echo "API: http://localhost:9001"
	@echo "UI: http://localhost:8501"
	@echo "MLflow: http://localhost:5000"
	docker-compose up --build

# Smoke tests (combination of open-trading, test-order, and test-logs)
smoke:
	@echo "Running smoke tests..."
	@echo "Step 1: Opening trading hours..."
	@$(MAKE) open-trading
	@echo ""
	@echo "Step 2: Testing order placement..."
	@$(MAKE) test-order
	@echo ""
	@echo "Step 3: Testing trade logs..."
	@$(MAKE) test-logs
	@echo ""
	@echo "Smoke tests completed successfully!"

# Full system check
full-check:
	@echo "Running full system check..."
	@echo "=========================================="
	@echo ""
	@echo "Step 1: System reset..."
	@$(MAKE) reset
	@echo ""
	@echo "Step 2: Health check..."
	@$(MAKE) health
	@echo ""
	@echo "Step 3: Routes check..."
	@$(MAKE) routes
	@echo ""
	@echo "Step 4: Smoke tests..."
	@$(MAKE) smoke
	@echo ""
	@echo "Step 5: Dataset building..."
	@$(MAKE) dataset
	@echo ""
	@echo "Step 6: Model training..."
	@$(MAKE) train
	@echo ""
	@echo "Step 7: Model status check..."
	@$(MAKE) model-status
	@echo ""
	@echo "=========================================="
	@echo "Full system check completed successfully!"
	@echo "All systems are operational and ready for trading."

# Log monitoring
logs-api:
	@echo "Tailing API server logs..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	@if [ -f "logs/api.log" ]; then \
		tail -f logs/api.log; \
	elif [ -f "logs/app.log" ]; then \
		tail -f logs/app.log; \
	else \
		echo "No API log file found. Looking for logs in:"; \
		echo "  - logs/api.log"; \
		echo "  - logs/app.log"; \
		echo "  - logs/"; \
		echo ""; \
		echo "Available log files:"; \
		find logs -name "*.log" 2>/dev/null || echo "No log files found in logs/ directory"; \
		echo ""; \
		echo "To start the API server with logging, run: make run-api"; \
	fi

logs-ui:
	@echo "Tailing Streamlit UI logs..."
	@echo "Press Ctrl+C to stop"
	@echo ""
	@if [ -f "logs/ui.log" ]; then \
		tail -f logs/ui.log; \
	elif [ -f "logs/streamlit.log" ]; then \
		tail -f logs/streamlit.log; \
	else \
		echo "No UI log file found. Looking for logs in:"; \
		echo "  - logs/ui.log"; \
		echo "  - logs/streamlit.log"; \
		echo "  - logs/"; \
		echo ""; \
		echo "Available log files:"; \
		find logs -name "*.log" 2>/dev/null || echo "No log files found in logs/ directory"; \
		echo ""; \
		echo "To start the UI with logging, run: make run-ui"; \
	fi

# NQ Futures Pipeline
nq-backfill:
	@echo "Generating NQ breakout trades from CSV data..."
	@if [ ! -f "data/raw/nq_1m.csv" ]; then \
		echo "Error: NQ CSV file not found at data/raw/nq_1m.csv"; \
		echo "Please place your 1-minute NQ data at this location with columns:"; \
		echo "  ts, open, high, low, close, volume, symbol, timeframe"; \
		exit 1; \
	fi
	python scripts/backfill_nq_from_csv.py

nq-dataset:
	@echo "Building dataset from NQ trades (excluding seed data)..."
	EXCLUDE_SEED=0 python engines/supervised/build_dataset.py

nq-train:
	@echo "Training model on NQ dataset..."
	python engines/supervised/train.py

nq-all: nq-backfill nq-dataset nq-train
	@echo ""
	@echo "✅ NQ backfill + dataset + train complete"
	@echo "Check model status: curl -s http://localhost:9001/v1/model/status | jq"
