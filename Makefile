# Makefile for Surah Splitter Docker Operations
# Run 'make help' to see available commands

.PHONY: help up down restart build clean logs shell status health test lint format

# Variables
DOCKER_COMPOSE = docker compose
PROJECT_NAME = surah-splitter
SERVICE = surah-splitter

# Color output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

## Help
help: ## Show this help message
	@echo "$(BLUE)════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Surah Splitter - Docker Management$(NC)"
	@echo "$(BLUE)════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "$(YELLOW)Available commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Usage examples:$(NC)"
	@echo "  make up               # Start the application"
	@echo "  make logs             # View application logs"
	@echo "  make shell            # Open shell in container"
	@echo ""

# Basic Commands
## Start services
up: ## Start the application
	@echo "$(YELLOW)Starting Surah Splitter...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Application started at http://localhost:8001$(NC)"
	@echo "$(GREEN)✓ API Docs available at http://localhost:8001/docs$(NC)"
	@echo "$(GREEN)✓ Demo Interface at http://localhost:8001/demo$(NC)"

## Stop services
down: ## Stop the application
	@echo "$(YELLOW)Stopping Surah Splitter...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Application stopped$(NC)"

## Restart services
restart: ## Restart the application
	@make down
	@sleep 2
	@make up

## Build images
build: ## Build or rebuild Docker image
	@echo "$(YELLOW)Building Docker image...$(NC)"
	@$(DOCKER_COMPOSE) build
	@echo "$(GREEN)✓ Build complete$(NC)"

## Rebuild and start
rebuild: ## Rebuild image and start application
	@echo "$(YELLOW)Rebuilding and starting...$(NC)"
	@$(DOCKER_COMPOSE) up -d --build
	@echo "$(GREEN)✓ Application rebuilt and started$(NC)"

## Clean everything
clean: ## Remove containers, volumes, and images
	@echo "$(RED)⚠️  This will remove all containers, volumes, and images!$(NC)"
	@read -p "Are you sure? (y/N): " confirm && \
	if [ "$$confirm" = "y" ]; then \
		$(DOCKER_COMPOSE) down -v --rmi all --remove-orphans; \
		echo "$(GREEN)✓ Cleanup complete$(NC)"; \
	else \
		echo "$(YELLOW)Cleanup cancelled$(NC)"; \
	fi

# Monitoring Commands
## View logs
logs: ## View application logs
	@$(DOCKER_COMPOSE) logs -f

## Show status
status: ## Show container status
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@echo "$(GREEN)  Container Status$(NC)"
	@echo "$(BLUE)════════════════════════════════════════$(NC)"
	@$(DOCKER_COMPOSE) ps

## Health check
health: ## Check application health
	@echo "$(YELLOW)Checking application health...$(NC)"
	@curl -f -s http://localhost:8001/health > /dev/null 2>&1 && \
		echo "$(GREEN)✓ API is healthy$(NC)" || \
		echo "$(RED)✗ API is not responding$(NC)"

## Open shell
shell: ## Open shell in container
	@$(DOCKER_COMPOSE) exec $(SERVICE) /bin/bash

## Execute command
exec: ## Execute command in container (use CMD="command")
	@if [ -z "$(CMD)" ]; then \
		echo "$(RED)Error: CMD variable required$(NC)"; \
		echo "Usage: make exec CMD=\"your command\""; \
	else \
		$(DOCKER_COMPOSE) exec $(SERVICE) sh -c "$(CMD)"; \
	fi

# Development Commands
## Run tests
test: ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	@$(DOCKER_COMPOSE) exec $(SERVICE) python -m pytest
	@echo "$(GREEN)✓ Tests complete$(NC)"

## Run linting
lint: ## Run code linting
	@echo "$(YELLOW)Running linters...$(NC)"
	@$(DOCKER_COMPOSE) exec $(SERVICE) ruff check src/
	@echo "$(GREEN)✓ Linting complete$(NC)"

## Format code
format: ## Format code
	@echo "$(YELLOW)Formatting code...$(NC)"
	@$(DOCKER_COMPOSE) exec $(SERVICE) ruff format src/
	@echo "$(GREEN)✓ Formatting complete$(NC)"

## Install dependencies
install: ## Install/update dependencies
	@echo "$(YELLOW)Installing dependencies...$(NC)"
	@$(DOCKER_COMPOSE) exec $(SERVICE) uv sync
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

# Quick Commands (shortcuts)
u: up ## Shortcut for 'up'
d: down ## Shortcut for 'down'
r: restart ## Shortcut for 'restart'
l: logs ## Shortcut for 'logs'
s: status ## Shortcut for 'status'
b: build ## Shortcut for 'build'

# Special Targets
.SILENT: help
.EXPORT_ALL_VARIABLES: