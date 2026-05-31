from __future__ import annotations

import asyncio

from app.domain.models import VideoJob
from app.persistence.job_repository import JobRepository
from app.services.video_worker import VideoWorker


class JobService:
    def __init__(self, repo: JobRepository, worker: VideoWorker) -> None:
        self.repo = repo
        self.worker = worker

    def create_job(self, query: str, topic: str = "chemistry") -> VideoJob:
        job = VideoJob(query=query, topic=topic)
        self.repo.create(job)
        asyncio.create_task(self.worker.process(job.id))
        return job

    def get_job(self, job_id: str) -> VideoJob:
        return self.repo.get(job_id)

    def list_jobs(self, status: str | None = None) -> list[VideoJob]:
        return self.repo.list(status=status)
