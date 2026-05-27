from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.schemas import CreateVideoRequest, CreateVideoResponse, VideoJobResponse
from app.container import get_job_service
from app.domain.exceptions import JobNotFoundError
from app.domain.models import JobStatus

router = APIRouter(prefix="/v1/videos", tags=["videos"])


@router.post("", response_model=CreateVideoResponse, status_code=202)
async def create_video(payload: CreateVideoRequest) -> CreateVideoResponse:
    service = get_job_service()
    job = service.create_job(query=payload.query, topic=payload.topic)
    return CreateVideoResponse(
        job_id=job.id,
        status=job.status,
        accepted_query=job.query,
        created_at=job.created_at,
    )


@router.get("", response_model=list[VideoJobResponse])
async def list_videos(status: str | None = Query(default=None)) -> list[VideoJobResponse]:
    service = get_job_service()
    return [VideoJobResponse(**job.model_dump()) for job in service.list_jobs(status=status)]


@router.get("/{job_id}", response_model=VideoJobResponse)
async def get_video(job_id: str) -> VideoJobResponse:
    service = get_job_service()
    try:
        return VideoJobResponse(**service.get_job(job_id).model_dump())
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{job_id}/artifact")
async def get_artifact(job_id: str) -> FileResponse:
    service = get_job_service()
    try:
        job = service.get_job(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if job.status != JobStatus.COMPLETED or not job.artifact:
        raise HTTPException(status_code=409, detail=f"Job is not completed. Current status={job.status.value}")

    return FileResponse(job.artifact.video_path, media_type="video/mp4", filename=f"{job.id}.mp4")
