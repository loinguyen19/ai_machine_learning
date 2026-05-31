from __future__ import annotations

from pathlib import Path

from ai_agent_video_generation.ai_agent_chemistry.app.domain.models import VideoJob
from ai_agent_video_generation.ai_agent_chemistry.app.generation.validators import REQUIRED_QUERIES


def evaluate_job(job: VideoJob) -> dict:
    """Score a completed (or failed) job against challenge success dimensions."""
    checks: dict[str, dict] = {}

    checks["helpful"] = _check_helpful(job)
    checks["consistent"] = _check_consistent(job)
    checks["guardrails"] = _check_guardrails(job)
    checks["explainable"] = _check_explainable(job)
    checks["cost_efficient"] = _check_cost_efficient(job)
    checks["reliable"] = _check_reliable(job)
    checks["educational"] = _check_educational(job)

    passed = sum(1 for item in checks.values() if item["passed"])
    return {
        "job_id": job.id,
        "status": job.status.value,
        "score": f"{passed}/{len(checks)}",
        "passed_all": passed == len(checks),
        "checks": checks,
    }


def _check_helpful(job: VideoJob) -> dict:
    passed = job.status.value == "completed" and bool(job.script)
    detail = "Job completed with structured script scenes." if passed else "Job did not complete with usable script."
    return {"passed": passed, "detail": detail}


def _check_consistent(job: VideoJob) -> dict:
    scenes = (job.script or {}).get("scenes", [])
    passed = len(scenes) >= 3
    return {
        "passed": passed,
        "detail": f"Scene count={len(scenes)} (expected >=3 for stable explainer format).",
    }


def _check_guardrails(job: VideoJob) -> dict:
    if job.query not in REQUIRED_QUERIES:
        return {"passed": False, "detail": "Query is outside required allowlist."}
    if not job.script:
        return {"passed": False, "detail": "No script to validate."}
    narration = " ".join(scene.get("narration", "") for scene in job.script.get("scenes", [])).lower()
    missing = [term for term in REQUIRED_QUERIES[job.query] if term.lower() not in narration]
    passed = not missing
    return {
        "passed": passed,
        "detail": "All required relevance terms present." if passed else f"Missing terms: {missing}",
    }


def _check_explainable(job: VideoJob) -> dict:
    has_events = len(job.events) > 0
    has_failure = bool(job.failed_step or job.error_message)
    passed = has_events or has_failure
    return {
        "passed": passed,
        "detail": f"events={len(job.events)}, failed_step={job.failed_step}, error={job.error_message}",
    }


def _check_cost_efficient(job: VideoJob) -> dict:
    cost = job.artifact.cost_estimate_usd if job.artifact else 0.0
    passed = cost < 0.05
    return {"passed": passed, "detail": f"estimated_cost_usd={cost:.6f} (target < 0.05)"}


def _check_reliable(job: VideoJob) -> dict:
    artifact_exists = bool(job.artifact and Path(job.artifact.video_path).exists())
    valid_mp4 = artifact_exists and Path(job.artifact.video_path).stat().st_size > 1000  # type: ignore[union-attr]
    passed = job.status.value == "completed" and valid_mp4
    return {
        "passed": passed,
        "detail": "Playable MP4 artifact exists." if passed else "Missing or invalid MP4 artifact.",
    }


def _check_educational(job: VideoJob) -> dict:
    scenes = (job.script or {}).get("scenes", [])
    has_narration = all(scene.get("narration") for scene in scenes)
    has_on_screen = all(scene.get("on_screen_text") for scene in scenes)
    passed = bool(scenes) and has_narration and has_on_screen
    return {
        "passed": passed,
        "detail": "Each scene has narration and on-screen text." if passed else "Missing narration/on-screen content.",
    }
