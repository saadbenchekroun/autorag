.PHONY: setup lint test run-backend run-frontend clean docker-up docker-down

setup:
	python -m pip install -e ".[dev]"
	pre-commit install
	cd frontend && npm install

lint:
	pre-commit run --all-files

test:
	pytest tests/

run-backend:
	uvicorn src.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -r {} +
	rm -rf frontend/.next frontend/node_modules

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down
