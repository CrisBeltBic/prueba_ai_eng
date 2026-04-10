import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    base_url: str = os.getenv("BANCOLOMBIA_BASE_URL", "https://www.bancolombia.com")
    start_path: str = os.getenv("BANCOLOMBIA_START_PATH", "/personas")
    user_agent: str = os.getenv("SCRAPER_USER_AGENT", "Mozilla/5.0 (compatible; BancolombiaRAG/1.0)")
    max_concurrent: int = int(os.getenv("SCRAPER_MAX_CONCURRENT", "2"))
    delay: float = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.0"))
    max_pages: int = int(os.getenv("SCRAPER_MAX_PAGES", "200"))
    raw_file: Path = Path(os.getenv("SCRAPER_RAW_FILE", "data/pages.jsonl"))


settings = Settings()
