import uuid
from datetime import datetime
from typing import Dict, Optional
from ai_agent_video_generation.claude.app.models import JobResponse, JobStatus

class JobStore:
    def __init__(self):
        self._jobs: Dict[str, JobResponse] = {}

    def create_job(self, concept: str) -> JobResponse:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        job = JobResponse(
            job_id=job_id,
            concept=concept,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobResponse]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[JobResponse]:
        return list(self._jobs.values())

    def update_status(self, job_id: str, status: JobStatus, **kwargs):
        job = self._jobs[job_id]
        updated = job.model_copy(update={"status": status, "updated_at": datetime.utcnow(), **kwargs})
        self._jobs[job_id] = updated
        return updated

# Singleton — in production, swap with a DB-backed implementation
job_store = JobStore()