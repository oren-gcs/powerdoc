.PHONY: help install setup clean test lint format docker-up docker-down deploy

help:
	@echo "Doc-Power Production Makefile"
	@echo "============================="
	@echo "  make install       - Install project dependencies (not used in Docker setup)"
	@echo "  make setup         - Setup development environment (not used in Docker setup)"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make test          - Run all tests (inside Docker)"
	@echo "  make lint          - Run linters (inside Docker)"
	@echo "  make format        - Format code (inside Docker)"
	@echo "  make docker-up     - Start all services with Docker Compose"
	@echo "  make docker-down   - Stop all services and remove containers"
	@echo "  make deploy        - Deploy to production (placeholder)"

# These commands are placeholders for running tasks locally.
# With a full Docker setup, you'd typically run these *inside* the containers.
# For example: docker-compose exec api-gateway pytest
install:
	@echo "Dependencies are installed via 'docker-compose build'"

setup:
	@echo "Environment is set up via 'docker-compose up'"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + || true
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ htmlcov/

test:
	@echo "Running tests in all services..."
	docker-compose exec api-gateway pytest
	docker-compose exec auth-service pytest
	# ... (add all other services)
	@echo "Tests complete."

lint:
	@echo "Linting all services..."
	docker-compose exec api-gateway flake8 .
	docker-compose exec auth-service flake8 .
	# ... (add all other services)
	@echo "Linting complete."

format:
	@echo "Formatting all services..."
	docker-compose exec api-gateway black .
	docker-compose exec auth-service black .
	# ... (add all other services)
	@echo "Formatting complete."

docker-up:
	@echo "Starting all services with Docker Compose..."
	docker-compose -f docker-compose.yml up -d --build

docker-down:
	@echo "Stopping all services and removing containers..."
	docker-compose -f docker-compose.yml down

deploy:
	@echo "Deploying to production..."
	# This is a placeholder. Real deployment would run:
	# bash scripts/kubernetes/deploy.sh prod
	@echo "Production deployment script would run here."

.DEFAULT_GOAL := help
