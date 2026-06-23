from __future__ import annotations
import io
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont

from paths import run_scenes_dir
from planner.plan_schema import SceneSpec

SLIDE_SIZE = (1280, 720)
BACKGROUND = (14, 22, 42)
TITLE_COLOR = (255, 255, 255)
BODY_COLOR = (230, 238, 255)
ACCENT_COLOR = (100, 180, 255)
TEXT_PANEL = (20, 34, 62)


class SceneRenderer:
    def __init__(self, tavily_client=None) -> None:
        self._tavily = tavily_client

    def render_scenes(
        self,
        plan_id: str,
        scenes: list[SceneSpec],
    ) -> list[str]:
        if not 3 <= len(scenes) <= 5:
            raise ValueError("Must provide between 3 and 5 scenes.")

        out_dir = run_scenes_dir(plan_id)
        raw_dir = out_dir / "raw"
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_dir.mkdir(parents=True, exist_ok=True)

        paths: list[str] = []
        total = len(scenes)
        for idx, scene in enumerate(scenes, start=1):
            image_path = out_dir / f"scene_{idx:02d}.png"
            photo = self._fetch_scene_image(scene, raw_dir / f"scene_{idx:02d}.jpg")
            self._render_card(
                image_path,
                scene=scene,
                photo=photo,
                scene_num=idx,
                total=total,
            )
            paths.append(str(image_path))
        return paths

    def _fetch_scene_image(self, scene: SceneSpec, cache_path: Path) -> Image.Image | None:
        if cache_path.exists():
            try:
                return Image.open(cache_path).convert("RGB")
            except OSError:
                pass

        if not self._tavily:
            return None

        try:
            response = self._tavily.search(
                query=f"{scene.image_search_query} {scene.location} photo",
                max_results=3,
                include_images=True,
            )
        except Exception:
            return None

        image_urls: list[str] = []
        for result in response.get("results", []):
            image_urls.extend(result.get("images", []) or [])
        image_urls.extend(response.get("images", []) or [])

        for url in image_urls:
            try:
                resp = requests.get(url, timeout=10, headers={"User-Agent": "HolidayPlanner/1.0"})
                resp.raise_for_status()
                img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                img.save(cache_path, format="JPEG", quality=85)
                return img
            except Exception:
                continue
        return None

    def _render_card(
        self,
        path: Path,
        *,
        scene: SceneSpec,
        photo: Image.Image | None,
        scene_num: int,
        total: int,
    ) -> None:
        image = Image.new("RGB", SLIDE_SIZE, BACKGROUND)
        draw = ImageDraw.Draw(image)
        title_font = self._load_font(28)
        body_font = self._load_font(20)
        small_font = self._load_font(16)

        draw.rectangle([0, 0, SLIDE_SIZE[0], 72], fill=(22, 38, 72))
        draw.text((32, 18), scene.title, fill=TITLE_COLOR, font=title_font)
        draw.text(
            (SLIDE_SIZE[0] - 130, 24),
            f"Scene {scene_num}/{total}",
            fill=ACCENT_COLOR,
            font=small_font,
        )

        if photo:
            photo_panel = (500, 96, 1248, 660)
            fitted = self._fit_image(photo, photo_panel)
            image.paste(fitted, (photo_panel[0], photo_panel[1]))
            draw.rounded_rectangle(photo_panel, radius=14, outline=ACCENT_COLOR, width=2)
        else:
            visual_box = (500, 96, 1248, 660)
            draw.rounded_rectangle(visual_box, radius=14, fill=(30, 50, 90), outline=ACCENT_COLOR, width=2)
            draw.text((530, 340), scene.location, fill=ACCENT_COLOR, font=title_font)

        text_x0, text_y0, text_x1, text_y1 = 32, 96, 470, 660
        draw.rounded_rectangle(
            [text_x0, text_y0, text_x1, text_y1],
            radius=14,
            fill=TEXT_PANEL,
            outline=ACCENT_COLOR,
            width=2,
        )
        day_label = f"Day {scene.day_number}" if scene.day_number else "Highlight"
        draw.text((text_x0 + 20, text_y0 + 20), day_label, fill=ACCENT_COLOR, font=small_font)
        draw.text((text_x0 + 20, text_y0 + 52), scene.location, fill=TITLE_COLOR, font=body_font)

        y = text_y0 + 92
        for line in self._wrap_text(scene.caption, max_chars=30):
            draw.text((text_x0 + 20, y), line, fill=BODY_COLOR, font=body_font)
            y += 30

        draw.rectangle([0, 684, SLIDE_SIZE[0], SLIDE_SIZE[1]], fill=(22, 38, 72))
        draw.text((32, 692), "Holiday Planner — Destination Preview", fill=ACCENT_COLOR, font=small_font)
        image.save(path)

    @staticmethod
    def _fit_image(photo: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
        x0, y0, x1, y1 = box
        target_w, target_h = x1 - x0, y1 - y0
        ratio = min(target_w / photo.width, target_h / photo.height)
        new_size = (max(1, int(photo.width * ratio)), max(1, int(photo.height * ratio)))
        resized = photo.resize(new_size, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (target_w, target_h), (30, 50, 90))
        offset = ((target_w - new_size[0]) // 2, (target_h - new_size[1]) // 2)
        canvas.paste(resized, offset)
        return canvas

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
