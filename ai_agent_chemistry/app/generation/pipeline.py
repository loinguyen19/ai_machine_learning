from __future__ import annotations

from pathlib import Path

from app.generation.assembler import VideoAssembler
from app.generation.script_generator import ScriptGenerator
from app.generation.slide_builder import SlideBuilder
from app.generation.tts import TTSProvider
from app.generation.validators import validate_script


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

    def run(self, query: str, work_dir: Path, output_path: Path) -> dict:
        script = self.script_generator.generate(query)
        validate_script(query, script)

        self.slide_builder.build_slides(script, work_dir)
        self.tts_provider.synthesize(script, work_dir)

        duration = sum(max(1, int(scene.get("duration_sec", 8))) for scene in script["scenes"])
        self.assembler.assemble(duration_sec=duration, output_path=output_path)

        return {
            "script": script,
            "duration_sec": duration,
            "estimated_cost_usd": 0.01,
        }
