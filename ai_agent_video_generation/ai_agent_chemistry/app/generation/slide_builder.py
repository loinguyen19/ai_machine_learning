from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from ai_agent_video_generation.ai_agent_chemistry.app.generation.diagrams import draw_visual

SLIDE_SIZE = (1280, 720)
BACKGROUND = (14, 22, 42)
TITLE_COLOR = (255, 255, 255)
BODY_COLOR = (230, 238, 255)
ACCENT_COLOR = (100, 180, 255)
TEXT_PANEL = (20, 34, 62)


class SlideBuilder:
    def build_slides(self, script: dict, work_dir: Path) -> list[Path]:
        slides: list[Path] = []
        title = script.get("title", "Chemistry Explainer")
        total = len(script.get("scenes", []))
        for idx, scene in enumerate(script.get("scenes", []), start=1):
            slide_path = work_dir / f"scene_{idx:02d}.png"
            self._render_slide(
                slide_path,
                title=title,
                body=scene.get("on_screen_text", ""),
                visual=scene.get("visual", "generic"),
                scene_num=idx,
                total=total,
            )
            slides.append(slide_path)
        return slides

    def _render_slide(
        self,
        path: Path,
        *,
        title: str,
        body: str,
        visual: str,
        scene_num: int,
        total: int,
    ) -> None:
        image = Image.new("RGB", SLIDE_SIZE, BACKGROUND)
        draw = ImageDraw.Draw(image)
        title_font = self._load_font(28)
        body_font = self._load_font(22)
        small_font = self._load_font(16)

        draw.rectangle([0, 0, SLIDE_SIZE[0], 72], fill=(22, 38, 72))
        draw.text((32, 18), title, fill=TITLE_COLOR, font=title_font)
        draw.text((SLIDE_SIZE[0] - 130, 24), f"Scene {scene_num}/{total}", fill=ACCENT_COLOR, font=small_font)

        # Left text panel (~38% width)
        text_x0, text_y0, text_x1, text_y1 = 32, 96, 470, 660
        draw.rounded_rectangle([text_x0, text_y0, text_x1, text_y1], radius=14, fill=TEXT_PANEL, outline=ACCENT_COLOR, width=2)
        draw.text((text_x0 + 20, text_y0 + 20), "Key idea", fill=ACCENT_COLOR, font=small_font)
        y = text_y0 + 52
        for line in self._wrap_text(body, max_chars=28):
            draw.text((text_x0 + 20, y), line, fill=BODY_COLOR, font=body_font)
            y += 32

        # Right diagram panel (~58% width)
        visual_box = (500, 96, 1248, 660)
        draw_visual(draw, visual, visual_box)

        draw.rectangle([0, 684, SLIDE_SIZE[0], SLIDE_SIZE[1]], fill=(22, 38, 72))
        draw.text((32, 692), "Growtrics Chemistry Explainer", fill=ACCENT_COLOR, font=small_font)
        image.save(path)

    @staticmethod
    def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap_text(text: str, max_chars: int) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current: list[str] = []
        for word in words:
            candidate = " ".join([*current, word])
            if len(candidate) <= max_chars:
                current.append(word)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [word]
        if current:
            lines.append(" ".join(current))
        return lines
