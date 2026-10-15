.PHONY: start dev test format lint clean check

PORT ?= 8080

start:
	GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

dev:
	GOOGLE_API_USE_CLIENT_CERTIFICATE=false uv run uvicorn app.main:app --reload --host 0.0.0.0 --port $(PORT)

test:
	DISABLE_LIVE_FIRESTORE=true uv run pytest -v

format:
	uv run ruff format .

lint:
	uv run ruff check . && uv run ruff format --check .

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ app/__pycache__ app/services/__pycache__ tests/__pycache__

check: format lint test
