"""
Settings for scraper_service.

All values are read from the service's own .env file (loaded at import time).
Tune SCRAPER_MAX_PAGES and SCRAPER_DELAY_SECONDS to control politeness;
the BFS crawler respects robots.txt regardless of these values.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    # Root of the site — used to build absolute URLs and to fetch robots.txt.
    base_url: str = os.getenv("BANCOLOMBIA_BASE_URL", "https://www.bancolombia.com")

    # BFS starts here. Only pages under this path are followed.
    start_path: str = os.getenv("BANCOLOMBIA_START_PATH", "/personas")

    # Identifies the bot in HTTP requests and is checked against robots.txt rules.
    user_agent: str = os.getenv("SCRAPER_USER_AGENT", "Mozilla/5.0 (compatible; BancolombiaRAG/1.0)")

    # Max simultaneous open connections. Keep low to avoid overloading the target.
    max_concurrent: int = int(os.getenv("SCRAPER_MAX_CONCURRENT", "2"))

    # Seconds to wait between requests to the same host (politeness delay).
    delay: float = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.0"))

    # Hard cap on how many pages are visited. Prevents runaway crawls.
    max_pages: int = int(os.getenv("SCRAPER_MAX_PAGES", "200"))

    # Output file written by this service and read by vector_store_service.
    # Both services mount the same raw_data Docker volume.
    raw_file: Path = Path(os.getenv("SCRAPER_RAW_FILE", "data/pages.jsonl"))


settings = Settings()
