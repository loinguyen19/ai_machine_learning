from __future__ import annotations

from ai_agent_video_generation.ai_agent_chemistry.app.domain.exceptions import JobNotFoundError
from ai_agent_video_generation.ai_agent_chemistry.app.domain.models import VideoJob
from ai_agent_video_generation.ai_agent_chemistry.app.persistence.job_repository import JobRepository


class InMemoryJobRepository(JobRepository):
    def __init__(self) -> None:
        self._jobs: dict[str, VideoJob] = {}

    def create(self, job: VideoJob) -> VideoJob:
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> VideoJob:
        job = self._jobs.get(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job

    def list(self, status: str | None = None) -> list[VideoJob]:
        jobs = list(self._jobs.values())
        if status:
            jobs = [j for j in jobs if j.status.value == status]
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def update(self, job: VideoJob) -> VideoJob:
        if job.id not in self._jobs:
            raise JobNotFoundError(f"Job {job.id} not found")
        self._jobs[job.id] = job
        return job
