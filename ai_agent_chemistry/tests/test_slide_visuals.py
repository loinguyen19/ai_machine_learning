from pathlib import Path

from app.generation.script_generator import FALLBACK_SCRIPTS
from app.generation.slide_builder import SlideBuilder


def test_slides_include_visual_diagrams(tmp_path: Path) -> None:
    script = FALLBACK_SCRIPTS["How does the pH scale work?"]
    slides = SlideBuilder().build_slides(script, tmp_path)
    assert len(slides) == 4
    for slide in slides:
        assert slide.exists()
        assert slide.stat().st_size > 5000

    # Diagram panel should differ per scene (not identical blank slides).
    sizes = {slide.stat().st_size for slide in slides}
    assert len(sizes) >= 3
