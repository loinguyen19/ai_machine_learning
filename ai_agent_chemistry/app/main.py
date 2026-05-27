from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.videos import router as videos_router

app = FastAPI(title="AI Chemistry Video Request Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(videos_router)
