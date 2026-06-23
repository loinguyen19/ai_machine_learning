from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from tavily import TavilyClient

# Ensure src/ is on path when launched via stdio from agent.py
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from planner.artifact_store import publish_final_plan, save_run_materials
from planner.plan_schema import SceneSpec, TripPlan
from planner.scene_renderer import SceneRenderer
from rag.memory_store import MemoryStore
from rag.seed_history import load_client_profiles, seed_client_memory

load_dotenv(SRC_DIR.parent / ".env")

mcp = FastMCP("HolidayPlanner")
_memory = MemoryStore()
_tavily: TavilyClient | None = None


def _get_tavily() -> TavilyClient:
    global _tavily
    if _tavily is None:
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY is not set in environment.")
        _tavily = TavilyClient(api_key=api_key)
    return _tavily


@mcp.tool()
def tavily_web_search(query: str, max_results: int = 5, include_images: bool = False) -> str:
    """Search the web with Tavily for destination research, restaurants, attractions, and travel tips."""
    client = _get_tavily()
    response = client.search(
        query=query,
        max_results=max_results,
        include_images=include_images,
    )
    simplified = {
        "query": query,
        "answer": response.get("answer"),
        "results": [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content"),
            }
            for r in response.get("results", [])
        ],
        "images": response.get("images", [])[:5] if include_images else [],
    }
    return json.dumps(simplified, indent=2)


@mcp.tool()
def search_client_memory(query: str, client_id: str = "maria", n_results: int = 5) -> str:
    """Search mock historical chat memory (RAG) for client preferences, habits, and past trips."""
    hits = _memory.search(query, client_id=client_id, n_results=n_results)
    return json.dumps({"query": query, "client_id": client_id, "results": hits}, indent=2)


@mcp.tool()
def get_client_profile(client_id: str) -> str:
    """Return a deterministic profile summary for a mock client from seed data."""
    profiles = load_client_profiles()
    profile = profiles.get(client_id)
    if not profile:
        return json.dumps({"error": f"Unknown client_id: {client_id}", "available": list(profiles.keys())})
    return json.dumps({"client_id": client_id, **profile}, indent=2)


@mcp.tool()
def seed_client_memory_tool(force: bool = False) -> str:
    """Ingest or re-ingest mock chat history into the Chroma vector store."""
    result = seed_client_memory(force=force)
    return json.dumps(result, indent=2)


@mcp.tool()
def render_destination_scenes(work_id: str, scenes_json: str) -> str:
    """Render 3-5 destination scene preview cards to artifacts/scenes/{work_id}/."""
    try:
        raw = json.loads(scenes_json) if isinstance(scenes_json, str) else scenes_json
        if isinstance(raw, dict) and "scenes" in raw:
            raw = raw["scenes"]
        scenes = [SceneSpec.model_validate(item) for item in raw]
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Invalid scenes JSON: {exc}"})

    try:
        renderer = SceneRenderer(tavily_client=_get_tavily())
        paths = renderer.render_scenes(work_id, scenes)
    except ValueError as exc:
        return json.dumps({"status": "error", "message": str(exc)})
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Render failed: {exc}"})

    return json.dumps(
        {
            "status": "rendered",
            "work_id": work_id,
            "scene_count": len(paths),
            "scenes_dir": str(Path(paths[0]).parent) if paths else "",
            "paths": paths,
        },
        indent=2,
    )


@mcp.tool()
def save_holiday_plan(work_id: str, plan_json: str) -> str:
    """Save plan materials to artifacts/scenes/{work_id}/, PDF to artifacts/pdf/{work_id}/plan.pdf, and overwrite final_plan/."""
    try:
        payload = json.loads(plan_json) if isinstance(plan_json, str) else plan_json
        if "plan_id" not in payload:
            payload["plan_id"] = work_id
        plan = TripPlan.model_validate(payload)
        if plan.plan_id != work_id:
            plan = plan.model_copy(update={"plan_id": work_id})
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Invalid plan JSON: {exc}"})

    try:
        saved = save_run_materials(plan)
        final = publish_final_plan(work_id)
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"Save failed: {exc}"})

    return json.dumps(
        {
            "status": "saved",
            "work_id": work_id,
            **saved,
            "final_plan": final,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
