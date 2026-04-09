.PHONY: run ingest stop test lint format

run:
	docker compose up --build

ingest:
	docker compose --profile pipeline up ingestion_service --build

stop:
	docker compose down

test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .