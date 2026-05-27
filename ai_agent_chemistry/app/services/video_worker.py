from __future__ import annotations

import asyncio
from pathlib import Path

from app.domain.models import JobStatus, VideoArtifact
from app.generation.pipeline import GenerationPipeline
from app.generation.script_generator import FALLBACK_SCRIPTS
from app.generation.validators import validate_query
from app.persistence.job_repository import JobRepository
from app.storage.artifact_store import ArtifactStore


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
        work_dir = Path(self.artifact_store.root) / "work" / job_id
        work_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.artifact_store.video_path(job_id)

        try:
            job.transition(JobStatus.VALIDATING)
            self.repo.update(job)
            validate_query(job.query)

            while job.attempt_count < self.max_attempts:
                job.attempt_count += 1
                self.repo.update(job)
                try:
                    job.transition(JobStatus.GENERATING_SCRIPT)
                    self.repo.update(job)
                    result = self.pipeline.run(query=job.query, work_dir=work_dir, output_path=output_path)
                    job.script = result["script"]
                    break
                except Exception as exc:  # noqa: BLE001
                    if job.attempt_count >= self.max_attempts:
                        # Last attempt fallback uses deterministic local template.
                        job.script = FALLBACK_SCRIPTS[job.query]
                        break
                    await asyncio.sleep(job.attempt_count)

            job.transition(JobStatus.GENERATING_MEDIA)
            self.repo.update(job)
            job.transition(JobStatus.ASSEMBLING)
            self.repo.update(job)

            # Ensure output exists from pipeline/fallback assembly path.
            if not output_path.exists():
                # Run once against fallback script if prior assembly path failed.
                result = self.pipeline.run(query=job.query, work_dir=work_dir, output_path=output_path)
                job.script = result["script"]
                duration_sec = int(result["duration_sec"])
                cost_estimate_usd = float(result["estimated_cost_usd"])
            else:
                duration_sec = sum(max(1, int(s.get("duration_sec", 8))) for s in (job.script or {}).get("scenes", []))
                cost_estimate_usd = 0.01

            manifest_path = self.artifact_store.write_manifest(
                job_id,
                {
                    "query": job.query,
                    "topic": job.topic,
                    "script": job.script,
                    "duration_sec": duration_sec,
                    "estimated_cost_usd": cost_estimate_usd,
                },
            )
            job.artifact = VideoArtifact(
                video_path=str(output_path),
                manifest_path=manifest_path,
                duration_sec=duration_sec,
                cost_estimate_usd=cost_estimate_usd,
            )
            job.transition(JobStatus.COMPLETED)
            self.repo.update(job)
        except Exception as exc:  # noqa: BLE001
            job.failed_step = job.status.value
            job.error_code = "generation_error"
            job.error_message = str(exc)
            job.transition(JobStatus.FAILED)
            self.repo.update(job)
