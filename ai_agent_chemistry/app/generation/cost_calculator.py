from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GenerationCostBreakdown:
    script_usd: float = 0.0
    tts_usd: float = 0.0
    slides_usd: float = 0.0
    assembly_usd: float = 0.0
    script_source: str = "template"
    tts_provider: str = "gtts"
    slide_provider: str = "pillow"
    scene_count: int = 0
    narration_chars: int = 0

    @property
    def total_usd(self) -> float:
        return round(self.script_usd + self.tts_usd + self.slides_usd + self.assembly_usd, 6)

    def to_dict(self) -> dict:
        return {
            "script_usd": self.script_usd,
            "tts_usd": self.tts_usd,
            "slides_usd": self.slides_usd,
            "assembly_usd": self.assembly_usd,
            "total_usd": self.total_usd,
            "script_source": self.script_source,
            "tts_provider": self.tts_provider,
            "slide_provider": self.slide_provider,
            "scene_count": self.scene_count,
            "narration_chars": self.narration_chars,
        }


# Rough production estimates used for metadata (not billing).
_LLM_COST_PER_1K_TOKENS = 0.00015
_OPENAI_TTS_PER_1K_CHARS = 0.015
_AVG_TOKENS_PER_SCENE = 120


def estimate_cost(
    script: dict,
    *,
    script_source: str = "template",
    tts_provider: str = "gtts",
    slide_provider: str = "pillow",
) -> GenerationCostBreakdown:
    scenes = script.get("scenes", [])
    narration = " ".join(scene.get("narration", "") for scene in scenes)
    narration_chars = len(narration)
    scene_count = len(scenes)

    if script_source == "llm":
        estimated_tokens = max(scene_count, 1) * _AVG_TOKENS_PER_SCENE + 200
        script_usd = (estimated_tokens / 1000) * _LLM_COST_PER_1K_TOKENS
    else:
        script_usd = 0.0

    if tts_provider == "openai":
        tts_usd = (narration_chars / 1000) * _OPENAI_TTS_PER_1K_CHARS
    else:
        tts_usd = 0.0

    return GenerationCostBreakdown(
        script_usd=round(script_usd, 6),
        tts_usd=round(tts_usd, 6),
        slides_usd=0.0,
        assembly_usd=0.0,
        script_source=script_source,
        tts_provider=tts_provider,
        slide_provider=slide_provider,
        scene_count=scene_count,
        narration_chars=narration_chars,
    )
