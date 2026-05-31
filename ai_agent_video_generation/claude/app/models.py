from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class VideoRequest(BaseModel):
    concept: str  # e.g. "How does the pH scale work?"

class JobResponse(BaseModel):
    job_id: str
    concept: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    artifact_path: Optional[str] = None
    error_message: Optional[str] = None
    cost_estimate_usd: Optional[float] = None