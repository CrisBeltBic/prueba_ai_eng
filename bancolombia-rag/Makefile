.PHONY: run stop pipeline logs-scraper logs-store logs-pipeline test lint format

# Runtime stack 
run:
	docker compose up --build

stop:
	docker compose down -v

# Data pipeline (scrape → embed → index)
pipeline:
	docker compose --profile pipeline up --build pipeline_runner

# Logs 
logs-scraper:
	docker compose logs -f scraper_service

logs-store:
	docker compose logs -f vector_store_service

logs-pipeline:
	docker compose logs -f pipeline_runner

# Quality 
test:
	pytest tests/ -v

lint:
	ruff check .

format:
	ruff format .
