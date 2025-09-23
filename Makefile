.PHONY: run lint format test seed-min seed-demo coverage

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check .
	mypy app

format:
	black .
	isort .

test:
	pytest -q --cov=app --cov-report=term-missing

coverage:
	pytest -q --cov=app --cov-report=term-missing --cov-report=html

seed-min:
	python scripts/seed_minimal.py

seed-demo:
	python scripts/seed_demo_data.py
