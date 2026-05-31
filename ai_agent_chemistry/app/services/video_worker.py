from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from app.domain.models import JobStatus, VideoArtifact
from app.generation.pipeline import GenerationPipeline
from app.generation.script_generator import FALLBACK_SCRIPTS
from app.generation.validators import validate_query
from app.persistence.job_repository import JobRepository
from app.services.job_observer import JobObserver
from app.storage.artifact_store import ArtifactStore

logger = logging.getLogger(__name__)


class VideoWorker:
    def __init__(
        self,
        repo: JobRepository,
        artifact_store: ArtifactStore,
        pipeline: GenerationPipeline | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.repo = repo
        self.artifact_store = artifact_store
        self.pipeline = pipeline or GenerationPipeline()
        self.max_attempts = max_attempts

    async def process(self, job_id: str) -> None:
        job = self.repo.get(job_id)
        observer = JobObserver(job)
        work_dir = Path(self.artifact_store.root) / "work" / job_id
        output_path = self.artifact_store.video_path(job_id)

        observer.log("queued", "Worker picked up job")

        try:
            observer.transition(JobStatus.VALIDATING, "Validating query against allowlist")
            validate_query(job.query)

            result: dict | None = None
            while job.attempt_count < self.max_attempts:
                job.attempt_count += 1
                self.repo.update(job)
                observer.log("generating_script", f"Generation attempt {job.attempt_count}/{self.max_attempts}")
                try:
                    result = self.pipeline.run(
                        query=job.query,
                        work_dir=work_dir,
                        output_path=output_path,
                        on_step=observer.pipeline_step,
                    )
                    job.script = result["script"]
                    break
                except Exception as exc:  # noqa: BLE001
                    observer.log("generating_script", f"Attempt failed: {exc}", level="warning")
                    if job.attempt_count >= self.max_attempts:
                        observer.log(
                            "generating_script",
                            "Using deterministic fallback script template",
                            level="warning",
                        )
                        job.script = FALLBACK_SCRIPTS[job.query]
                        result = self.pipeline.run(
                            query=job.query,
                            work_dir=work_dir,
                            output_path=output_path,
                            on_step=observer.pipeline_step,
                        )
                        job.script = result["script"]
                        break
                    await asyncio.sleep(job.attempt_count)

            if result is None:
                raise RuntimeError("Pipeline did not produce a result")

            if not output_path.exists():
                raise RuntimeError("Video artifact was not created")

            duration_sec = int(result["duration_sec"])
            cost_estimate_usd = float(result["estimated_cost_usd"])
            cost_breakdown = result.get("cost_breakdown")

            manifest_path = self.artifact_store.write_manifest(
                job_id,
                {
                    "query": job.query,
                    "topic": job.topic,
                    "script": job.script,
                    "duration_sec": duration_sec,
                    "estimated_cost_usd": cost_estimate_usd,
                    "cost_breakdown": cost_breakdown,
                    "events": [event.model_dump(mode="json") for event in job.events],
                },
            )
            job.artifact = VideoArtifact(
                video_path=str(output_path),
                manifest_path=manifest_path,
                duration_sec=duration_sec,
                cost_estimate_usd=cost_estimate_usd,
                cost_breakdown=cost_breakdown,
            )
            observer.transition(JobStatus.COMPLETED, f"Video ready at {output_path}")
            self.repo.update(job)
        except Exception as exc:  # noqa: BLE001
            observer.log(job.status.value, str(exc), level="error")
            job.failed_step = job.status.value
            job.error_code = "generation_error"
            job.error_message = str(exc)
            job.transition(JobStatus.FAILED)
            self.repo.update(job)
            logger.exception("Job %s failed", job_id)
