# SpecOps Makefile
#
# Development:   make dev        (or: make backend + make frontend in two terminals)
# Docs preview:  make docs       (VitePress at http://localhost:4173/specops/)
# Production:    make install && specops setup && specops serve
# Container:     make container  (uses docker by default, set ENGINE=podman for podman)
# Stop/cleanup:  make container-stop  (stops and removes all specops + agent containers)

# Container engine: docker (default) or podman
ENGINE ?= $(shell command -v docker >/dev/null 2>&1 && echo docker || echo podman)

.PHONY: install dev backend frontend docs docs-dev setup build test lint lint-fix format clean user-list user-create user-update user-set-password container container-nobuild container-clean container-logs container-stop

# ─────────────────────────────────────────────────────────────────────────────
# Installation
# ─────────────────────────────────────────────────────────────────────────────

install:
	@echo "Installing Python dependencies..."
	uv sync --group dev
	@echo "Installing frontend dependencies..."
	cd specops-ui && npm install
	@echo ""
	@echo "Installation complete. Next steps:"
	@echo "  1. specops setup              # Create admin user"
	@echo "  2. specops serve              # Start server"

# ─────────────────────────────────────────────────────────────────────────────
# Development (hot-reload)
# ─────────────────────────────────────────────────────────────────────────────

dev:
	@echo "Starting development servers..."
	@echo "  Backend:  http://localhost:8080"
	@echo "  Frontend: http://localhost:5173"
	@echo ""
	@echo "Run in two terminals: make backend | make frontend"

backend:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m specops.cli serve --host 127.0.0.1 --port 8080 --reload

frontend:
	cd specops-ui && npm run dev

docs:
	npm run docs:build && npm run docs:preview

docs-dev:
	npm run docs:dev

# ─────────────────────────────────────────────────────────────────────────────
# Setup & Production
# ─────────────────────────────────────────────────────────────────────────────

setup:
	ADMIN_STORAGE_ROOT=$$(pwd)/data ADMIN_SETUP_USERNAME=admin ADMIN_SETUP_PASSWORD=admin uv run python -m specops.cli setup

user-list:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m specops.cli user list

# Create user: make user-create CREATE_USER=alice CREATE_PASS=secret
user-create:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m specops.cli user create $(CREATE_USER) --password $(CREATE_PASS)

# Update user: make user-update UPDATE_USER=alice UPDATE_PASS=newpass
user-update:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m specops.cli user update $(UPDATE_USER) --password $(UPDATE_PASS)

# Reset password: make user-set-password RESET_USER=admin
user-set-password:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m specops.cli user set-password $(RESET_USER)

serve:
	ADMIN_STORAGE_ROOT=$$(pwd)/data uv run python -m specops.cli serve --port 8080

# Build production frontend (outputs directly to specops/static/)
build:
	cd specops-ui && npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Testing & Quality
# ─────────────────────────────────────────────────────────────────────────────

test:
	uv run python -m pytest tests/ -v

lint:
	uv run ruff check .
	uv run ruff format --check .

lint-fix:
	uv run ruff check . --fix

format:
	uv run ruff format .

# ─────────────────────────────────────────────────────────────────────────────
# Container (local) — set ENGINE=podman to use podman
# ─────────────────────────────────────────────────────────────────────────────

container:
	SPECOPS_ENGINE=$(ENGINE) ./scripts/dev.sh --logs

container-nobuild:
	SPECOPS_ENGINE=$(ENGINE) ./scripts/dev.sh --no-build --logs

container-clean:
	SPECOPS_ENGINE=$(ENGINE) ./scripts/dev.sh --clean --logs

container-logs:
	$(ENGINE) logs -f specops

container-stop:
	@echo "Stopping and removing specops containers..."
	-@AGENTS=$$($(ENGINE) ps -aq --filter "name=specialagent-" 2>/dev/null || true); \
	  [ -n "$$AGENTS" ] && echo "$$AGENTS" | xargs $(ENGINE) rm -f 2>/dev/null || true
	-@$(ENGINE) stop specops 2>/dev/null || true
	-@$(ENGINE) rm -f specops 2>/dev/null || true
	@echo "Done."

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
