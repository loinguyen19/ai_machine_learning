from __future__ import annotations
import logging
from fastapi import FastAPI
from ai_agent_video_generation.ai_agent_chemistry.app.api.routes.videos import router as videos_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

app = FastAPI(title="AI Chemistry Video Request Service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(videos_router)
