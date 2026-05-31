from ai_agent_video_generation.ai_agent_chemistry.app.domain.models import JobStatus, VideoArtifact, VideoJob
from ai_agent_video_generation.ai_agent_chemistry.app.generation.cost_calculator import estimate_cost
from ai_agent_video_generation.ai_agent_chemistry.app.generation.evaluation import evaluate_job


def test_estimate_cost_template_is_free() -> None:
    script = {
        "scenes": [
            {"narration": "The pH scale measures acidity.", "duration_sec": 8},
            {"narration": "Seven is neutral.", "duration_sec": 8},
        ]
    }
    cost = estimate_cost(script, script_source="template", tts_provider="gtts")
    assert cost.total_usd == 0.0
    assert cost.narration_chars > 0


def test_estimate_cost_llm_nonzero() -> None:
    script = {"scenes": [{"narration": "abc", "duration_sec": 8}]}
    cost = estimate_cost(script, script_source="llm", tts_provider="gtts")
    assert cost.total_usd > 0.0


def test_evaluate_completed_job() -> None:
    job = VideoJob(
        query="How does the pH scale work?",
        status=JobStatus.COMPLETED,
        script={
            "scenes": [
                {"narration": "pH acid base", "on_screen_text": "pH"},
                {"narration": "acid base scale", "on_screen_text": "scale"},
                {"narration": "acid base examples", "on_screen_text": "examples"},
            ]
        },
        artifact=VideoArtifact(
            video_path="/tmp/fake.mp4",
            manifest_path="/tmp/fake.json",
            duration_sec=30,
            cost_estimate_usd=0.0,
        ),
        events=[{"step": "completed", "message": "done", "status": "completed"}],
    )
    report = evaluate_job(job)
    assert "checks" in report
    assert report["checks"]["cost_efficient"]["passed"] is True
