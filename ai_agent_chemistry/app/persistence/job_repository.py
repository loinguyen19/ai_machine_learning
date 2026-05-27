from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import VideoJob


class JobRepository(ABC):
    @abstractmethod
    def create(self, job: VideoJob) -> VideoJob:
        raise NotImplementedError

    @abstractmethod
    def get(self, job_id: str) -> VideoJob:
        raise NotImplementedError

    @abstractmethod
    def list(self, status: str | None = None) -> list[VideoJob]:
        raise NotImplementedError

    @abstractmethod
    def update(self, job: VideoJob) -> VideoJob:
        raise NotImplementedError
