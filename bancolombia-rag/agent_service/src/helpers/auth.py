from fastapi import HTTPException, Request

from config import settings


def verify_api_key(request: Request) -> None:
    """Validate X-API-Key header. Skipped if AGENT_API_SERVICE_KEY is not set."""
    if settings.agent_api_service_key:
        key = request.headers.get("X-API-Key", "")
        if key != settings.agent_api_service_key:
            raise HTTPException(status_code=401, detail="Unauthorized")
