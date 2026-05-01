.PHONY: run test lint format deps test-unit test-integration test-e2e lint fix

SRC_DIR = app

deps:
	poetry lock
	poetry install --no-root

run:
	docker-compose up

test:
	cd app && PYTHONPATH=. pytest tests/

test-unit:
	cd app && PYTHONPATH=. pytest tests/unit/ -v

test-integration:
	cd app && PYTHONPATH=. pytest tests/integration/ -v

test-e2e:
	cd app && PYTHONPATH=. pytest tests/e2e/ -v

lint:
	@echo "🔎 Running Ruff linter..."
	@poetry run ruff check $(SRC_DIR) --no-cache --preview || true
	@echo "🔎 Running Mypy type check..."
	@poetry run mypy $(SRC_DIR) --no-incremental || true

fix:
	@echo "🛠️ Auto-fixing code..."
	@poetry run ruff check --preview --fix $(SRC_DIR)
	@echo "✅ Auto-fix completed."