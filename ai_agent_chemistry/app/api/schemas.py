from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import JobStatus, VideoArtifact


class CreateVideoRequest(BaseModel):
    query: str = Field(min_length=1)
    topic: str = "chemistry"


class CreateVideoResponse(BaseModel):
    job_id: str
    status: JobStatus
    accepted_query: str
    created_at: datetime


class VideoJobResponse(BaseModel):
    id: str
    query: str
    topic: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    attempt_count: int
    failed_step: str | None
    error_code: str | None
    error_message: str | None
    artifact: VideoArtifact | None
    script: dict[str, Any] | None
