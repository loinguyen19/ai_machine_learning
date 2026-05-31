from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_MEDIA = "generating_media"
    ASSEMBLING = "assembling"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoArtifact(BaseModel):
    video_path: str
    manifest_path: str
    duration_sec: int = 0
    cost_estimate_usd: float = 0.0
    cost_breakdown: dict[str, Any] | None = None


class JobEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step: str
    message: str
    status: str
    level: str = "info"


class VideoJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    query: str
    topic: str = "chemistry"
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attempt_count: int = 0
    failed_step: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    script: dict[str, Any] | None = None
    artifact: VideoArtifact | None = None
    events: list[JobEvent] = Field(default_factory=list)

    def transition(self, status: JobStatus) -> None:
        self.status = status
        self.updated_at = datetime.now(timezone.utc)
