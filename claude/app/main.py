from fastapi import FastAPI
from app.routers.videos import router as videos_router
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Chemistry Video Request Service",
    description="Submit chemistry concept requests and receive AI-generated educational videos.",
    version="1.0.0",
)

app.include_router(videos_router)


@app.get("/health")
def health():
    return {"status": "ok"}
