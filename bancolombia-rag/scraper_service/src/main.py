# -------------------------------------------------------------------------
# Copyright. All rights reserved.
# by Cristian Beltran
# --------------------------------------------------------------------------
import uvicorn
from fastapi import FastAPI

from scraper import api as scraper_api

app = FastAPI(title="Scraper Service")

app.include_router(scraper_api.router, prefix="/scraper", tags=["scraper"])


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8083, reload=True)

#docker build -t scraper_service .

#docker run --env-file .env -p 8083:8083 scraper_service

