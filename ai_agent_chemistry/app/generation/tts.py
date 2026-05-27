from __future__ import annotations

from pathlib import Path


class TTSProvider:
    def synthesize(self, script: dict, work_dir: Path) -> Path:
        # For this prototype we persist narration as transcript metadata.
        transcript = work_dir / "narration.txt"
        narration = "\n".join(scene.get("narration", "") for scene in script.get("scenes", []))
        transcript.write_text(narration, encoding="utf-8")
        return transcript
