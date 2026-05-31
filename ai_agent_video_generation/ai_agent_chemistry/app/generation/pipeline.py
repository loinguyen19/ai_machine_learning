from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv
from ai_agent_video_generation.ai_agent_chemistry.app.generation.assembler import VideoAssembler
from ai_agent_video_generation.ai_agent_chemistry.app.generation.cost_calculator import GenerationCostBreakdown, estimate_cost
from ai_agent_video_generation.ai_agent_chemistry.app.generation.script_generator import ScriptGenerator
from ai_agent_video_generation.ai_agent_chemistry.app.generation.slide_builder import SlideBuilder
from ai_agent_video_generation.ai_agent_chemistry.app.generation.tts import TTSProvider
from ai_agent_video_generation.ai_agent_chemistry.app.generation.validators import validate_script

logger = logging.getLogger(__name__)

StepCallback = Callable[[str, str], None]

load_dotenv()

class GenerationPipeline:
    def __init__(
        self,
        script_generator: ScriptGenerator | None = None,
        slide_builder: SlideBuilder | None = None,
        tts_provider: TTSProvider | None = None,
        assembler: VideoAssembler | None = None,
    ) -> None:
        self.script_generator = script_generator or ScriptGenerator()
        self.slide_builder = slide_builder or SlideBuilder()
        self.tts_provider = tts_provider or TTSProvider()
        self.assembler = assembler or VideoAssembler()
        self.script_source = "llm" if os.getenv("USE_LLM_SCRIPT") == "1" else "template"
        self.tts_provider_name = os.getenv("TTS_PROVIDER", "gtts")

    def run(
        self,
        query: str,
        work_dir: Path,
        output_path: Path,
        on_step: StepCallback | None = None,
    ) -> dict:
        work_dir.mkdir(parents=True, exist_ok=True)

        self._emit(on_step, "generating_script", "Generating structured script")
        script = self.script_generator.generate(query)
        validate_script(query, script)
        logger.info("Script generated with %s scenes", len(script.get("scenes", [])))

        self._emit(on_step, "generating_media", "Rendering slide images")
        self.slide_builder.build_slides(script, work_dir)

        self._emit(on_step, "generating_media", "Synthesizing narration audio")
        self.tts_provider.synthesize(script, work_dir)

        self._emit(on_step, "assembling", "Assembling MP4 from slides and audio")
        self.assembler.assemble(work_dir=work_dir, script=script, output_path=output_path)

        duration = sum(max(1, int(scene.get("duration_sec", 8))) for scene in script["scenes"])
        cost = estimate_cost(
            script,
            script_source=self.script_source,
            tts_provider=self.tts_provider_name,
        )

        return {
            "script": script,
            "duration_sec": duration,
            "estimated_cost_usd": cost.total_usd,
            "cost_breakdown": cost.to_dict(),
        }

    @staticmethod
    def _emit(on_step: StepCallback | None, step: str, message: str) -> None:
        logger.info("[%s] %s", step, message)
        if on_step:
            on_step(step, message)
