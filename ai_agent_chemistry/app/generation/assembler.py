from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.domain.exceptions import GenerationError


class VideoAssembler:
    def assemble(self, duration_sec: int, output_path: Path) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            # Fallback keeps the demo pipeline deterministic in constrained environments.
            output_path.write_bytes(b"placeholder-mp4")
            return

        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=1280x720:d={duration_sec}",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r=44100:cl=stereo:d={duration_sec}",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise GenerationError(f"ffmpeg failed: {result.stderr.strip()}")
