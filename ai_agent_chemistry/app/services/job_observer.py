from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.domain.models import JobEvent, JobStatus, VideoJob

logger = logging.getLogger(__name__)


class JobObserver:
    def __init__(self, job: VideoJob) -> None:
        self.job = job

    def log(self, step: str, message: str, *, level: str = "info") -> None:
        event = JobEvent(
            step=step,
            message=message,
            status=self.job.status.value,
            level=level,
        )
        self.job.events.append(event)
        log_fn = logger.info if level == "info" else logger.warning if level == "warning" else logger.error
        log_fn("job=%s status=%s step=%s %s", self.job.id, self.job.status.value, step, message)

    def transition(self, status: JobStatus, message: str) -> None:
        self.job.transition(status)
        self.log(step=status.value, message=message)

    def pipeline_step(self, step: str, message: str) -> None:
        if step == "generating_script":
            self.job.transition(JobStatus.GENERATING_SCRIPT)
        elif step == "generating_media":
            self.job.transition(JobStatus.GENERATING_MEDIA)
        elif step == "assembling":
            self.job.transition(JobStatus.ASSEMBLING)
        self.log(step=step, message=message)
