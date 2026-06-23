from __future__ import annotations

import json
import shutil
from pathlib import Path

from paths import FINAL_PLAN_DIR, run_pdf_dir, run_scenes_dir
from planner.pdf_builder import build_plan_pdf
from planner.plan_schema import TripPlan, trip_plan_to_markdown


def save_run_materials(plan: TripPlan) -> dict[str, str]:
    """Persist plan JSON/Markdown under artifacts/scenes/{work_id}/ and PDF under artifacts/pdf/{work_id}/."""
    work_id = plan.plan_id
    scenes_dir = run_scenes_dir(work_id)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    json_path = scenes_dir / "plan.json"
    md_path = scenes_dir / "plan.md"
    json_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(trip_plan_to_markdown(plan), encoding="utf-8")

    pdf_path = run_pdf_dir(work_id) / "plan.pdf"
    build_plan_pdf(plan, scenes_dir, pdf_path)

    return {
        "work_id": work_id,
        "json_path": str(json_path),
        "markdown_path": str(md_path),
        "pdf_path": str(pdf_path),
        "scenes_dir": str(scenes_dir),
    }


def publish_final_plan(work_id: str) -> dict[str, str]:
    """Overwrite final_plan/ with the latest run deliverables."""
    scenes_dir = run_scenes_dir(work_id)
    pdf_path = run_pdf_dir(work_id) / "plan.pdf"

    if FINAL_PLAN_DIR.exists():
        shutil.rmtree(FINAL_PLAN_DIR)
    FINAL_PLAN_DIR.mkdir(parents=True, exist_ok=True)

    final_scenes = FINAL_PLAN_DIR / "scenes"
    final_scenes.mkdir(parents=True, exist_ok=True)

    for src_name, dst in [
        (scenes_dir / "plan.json", FINAL_PLAN_DIR / "plan.json"),
        (scenes_dir / "plan.md", FINAL_PLAN_DIR / "plan.md"),
        (pdf_path, FINAL_PLAN_DIR / "plan.pdf"),
    ]:
        if src_name.exists():
            shutil.copy2(src_name, dst)

    for scene in sorted(scenes_dir.glob("scene_*.png")):
        shutil.copy2(scene, final_scenes / scene.name)

    outputs = {
        "work_id": work_id,
        "final_plan_dir": str(FINAL_PLAN_DIR),
        "json_path": str(FINAL_PLAN_DIR / "plan.json"),
        "markdown_path": str(FINAL_PLAN_DIR / "plan.md"),
        "pdf_path": str(FINAL_PLAN_DIR / "plan.pdf"),
        "scenes_dir": str(final_scenes),
    }
    (FINAL_PLAN_DIR / "manifest.json").write_text(json.dumps(outputs, indent=2), encoding="utf-8")
    outputs["manifest_path"] = str(FINAL_PLAN_DIR / "manifest.json")
    return outputs
