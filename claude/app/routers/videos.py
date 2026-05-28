from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.models import VideoRequest, JobResponse
from app.job_store import job_store
from app.generation.script_generator import validate_concept
from app.generation.pipeline import run_pipeline
from pathlib import Path

router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_CONCEPTS_MSG = (
    "Supported concepts: "
    "'How does the pH scale work?', "
    "'Why do atoms form covalent bonds?', "
    "'What is the difference between ionic and covalent bonding?'"
)


@router.post("/request", response_model=JobResponse, status_code=202)
async def request_video(body: VideoRequest, background_tasks: BackgroundTasks):
    if not validate_concept(body.concept):
        raise HTTPException(status_code=422, detail=f"Unsupported concept. {ALLOWED_CONCEPTS_MSG}")

    job = job_store.create_job(body.concept)
    background_tasks.add_task(run_pipeline, job.job_id, body.concept)
    return job


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs():
    return job_store.list_jobs()


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/download")
def download_video(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job is {job.status}, not completed yet")

    path = Path(job.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=500, detail="Artifact file missing")

    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")
