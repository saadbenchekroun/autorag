.PHONY: setup lint format test test-cov run-backend run-frontend clean docker-up docker-down docker-prod-up check

# ── Setup ─────────────────────────────────────────────────────────────────
setup:
	@echo "→ Checking Python version..."
	@python --version
	@echo "→ Installing Python dependencies..."
	python -m pip install -e ".[dev,cli]"
	@echo "→ Installing pre-commit hooks..."
	pre-commit install
	@echo "→ Creating required runtime directories..."
	@mkdir -p uploads chroma_db
	@if not exist .env (copy .env.example .env && echo "→ Created .env from .env.example — please fill in your API keys")
	@if exist frontend\package.json (cd frontend && npm install)
	@echo "✓ Setup complete."

# ── Code Quality ──────────────────────────────────────────────────────────
lint:
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

format:
	ruff format src/ tests/
	ruff check src/ tests/ --fix

check: lint test

# ── Testing ───────────────────────────────────────────────────────────────
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -v
	@echo "→ Coverage report: htmlcov/index.html"

# ── Running locally ───────────────────────────────────────────────────────
run-backend:
	uvicorn src.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

# ── Docker ────────────────────────────────────────────────────────────────
docker-up:
	docker-compose up --build -d
	@echo "→ API:      http://localhost:8000/api/v1/docs"
	@echo "→ Frontend: http://localhost:3000"

docker-down:
	docker-compose down

docker-prod-up:
	docker-compose -f docker-compose.prod.yml up --build -d

# ── Cleanup ───────────────────────────────────────────────────────────────
clean:
	@if exist __pycache__ (rmdir /s /q __pycache__)
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@if exist .pytest_cache (rmdir /s /q .pytest_cache)
	@if exist .mypy_cache (rmdir /s /q .mypy_cache)
	@if exist .ruff_cache (rmdir /s /q .ruff_cache)
	@if exist htmlcov (rmdir /s /q htmlcov)
	@echo "✓ Cleaned."
