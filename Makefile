.PHONY: install dev run test clean format lint docs help

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
PIP := pip
UVICORN := uvicorn

help: ## Show this help message
	@echo "Eco Draft 2D - Available commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	@echo "Installing dependencies..."
	$(PIP) install -e .
	@echo "Dependencies installed successfully!"

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PIP) install -e ".[dev]"
	@echo "Development dependencies installed successfully!"

dev: ## Run development server
	@echo "Starting development server..."
	$(PYTHON) -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

run: ## Run production server
	@echo "Starting production server..."
	$(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000

test: ## Run tests
	@echo "Running tests..."
	pytest -v

test-cov: ## Run tests with coverage
	@echo "Running tests with coverage..."
	pytest --cov=backend/app --cov-report=html --cov-report=term-missing

format: ## Format code with black and isort
	@echo "Formatting code..."
	black backend/
	isort backend/
	@echo "Code formatted successfully!"

lint: ## Lint code with flake8 and mypy
	@echo "Linting code..."
	flake8 backend/
	mypy backend/
	@echo "Linting completed!"

clean: ## Clean temporary files
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	@echo "Cleanup completed!"

docs: ## Generate documentation
	@echo "Generating documentation..."
	# Add documentation generation command here
	@echo "Documentation generated!"

docker-build: ## Build Docker image
	@echo "Building Docker image..."
	docker build -t eco-draft-2d .
	@echo "Docker image built successfully!"

docker-run: ## Run Docker container
	@echo "Running Docker container..."
	docker run -p 8000:8000 eco-draft-2d

setup: install ## Complete setup (alias for install)

check: lint test ## Run all checks (lint and test)

all: clean install format lint test ## Run complete workflow
