from __future__ import annotations

from ai_agent_video_generation.ai_agent_chemistry.app.persistence.memory_repository import InMemoryJobRepository
from ai_agent_video_generation.ai_agent_chemistry.app.services.job_service import JobService
from ai_agent_video_generation.ai_agent_chemistry.app.services.video_worker import VideoWorker
from ai_agent_video_generation.ai_agent_chemistry.app.storage.artifact_store import ArtifactStore

_repo = InMemoryJobRepository()
_artifact_store = ArtifactStore(root_dir="./artifacts")
_worker = VideoWorker(repo=_repo, artifact_store=_artifact_store)
_job_service = JobService(repo=_repo, worker=_worker)


def get_job_service() -> JobService:
    return _job_service
