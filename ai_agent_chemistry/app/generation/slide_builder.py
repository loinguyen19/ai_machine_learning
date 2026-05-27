from __future__ import annotations

from pathlib import Path


class SlideBuilder:
    def build_slides(self, script: dict, work_dir: Path) -> list[Path]:
        # Keep visuals deterministic and cheap: write scene text stubs as .txt assets.
        # A real implementation can swap this out for PNG renderers.
        slides: list[Path] = []
        for idx, scene in enumerate(script.get("scenes", []), start=1):
            slide = work_dir / f"scene_{idx:02d}.txt"
            slide.write_text(scene.get("on_screen_text", ""), encoding="utf-8")
            slides.append(slide)
        return slides
