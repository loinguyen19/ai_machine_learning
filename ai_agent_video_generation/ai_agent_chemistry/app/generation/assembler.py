from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ai_agent_video_generation.ai_agent_chemistry.app.domain.exceptions import GenerationError


class VideoAssembler:
    def assemble(self, work_dir: Path, script: dict, output_path: Path) -> None:
        slides = sorted(work_dir.glob("scene_*.png"))
        if not slides:
            raise GenerationError("No slide images found for assembly.")

        scenes = script.get("scenes", [])
        scene_clips: list[Path] = []
        for idx, slide in enumerate(slides, start=1):
            audio = self._find_audio(work_dir, idx)
            duration = max(2, int(scenes[idx - 1].get("duration_sec", 8)) if idx - 1 < len(scenes) else 8)
            clip_path = work_dir / f"clip_{idx:02d}.mp4"
            self._render_scene_clip(slide=slide, audio=audio, duration_sec=duration, output_path=clip_path)
            scene_clips.append(clip_path)

        self._concat_clips(scene_clips, output_path)

    def _find_audio(self, work_dir: Path, idx: int) -> Path | None:
        for ext in (".mp3", ".wav"):
            candidate = work_dir / f"scene_{idx:02d}{ext}"
            if candidate.exists():
                return candidate
        return None

    def _render_scene_clip(
        self,
        *,
        slide: Path,
        audio: Path | None,
        duration_sec: int,
        output_path: Path,
    ) -> None:
        ffmpeg = self._resolve_ffmpeg()
        if audio:
            cmd = [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-i",
                str(slide),
                "-i",
                str(audio),
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        else:
            cmd = [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-i",
                str(slide),
                "-f",
                "lavfi",
                "-i",
                f"anullsrc=r=44100:cl=stereo:d={duration_sec}",
                "-t",
                str(duration_sec),
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ]
        self._run_ffmpeg(cmd)

    def _concat_clips(self, clips: list[Path], output_path: Path) -> None:
        if len(clips) == 1:
            shutil.copyfile(clips[0], output_path)
            return

        ffmpeg = self._resolve_ffmpeg()
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
            list_path = Path(handle.name)
            for clip in clips:
                handle.write(f"file '{clip.resolve()}'\n")

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            str(output_path),
        ]
        try:
            self._run_ffmpeg(cmd)
        finally:
            list_path.unlink(missing_ok=True)

    @staticmethod
    def _resolve_ffmpeg() -> str:
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(
                "ffmpeg is required to assemble videos. Install ffmpeg (brew install ffmpeg) "
                "or pip install imageio-ffmpeg."
            ) from exc

    @staticmethod
    def _run_ffmpeg(cmd: list[str]) -> None:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise GenerationError(f"ffmpeg failed: {result.stderr.strip() or result.stdout.strip()}")
