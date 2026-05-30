from __future__ import annotations

import logging
import struct
import wave
from pathlib import Path

logger = logging.getLogger(__name__)


class TTSProvider:
    """Generates narration audio. gTTS is used for audio only — not visuals."""

    def synthesize(self, script: dict, work_dir: Path) -> list[Path]:
        transcript = work_dir / "narration.txt"
        narration = "\n".join(scene.get("narration", "") for scene in script.get("scenes", []))
        transcript.write_text(narration, encoding="utf-8")

        audio_paths: list[Path] = []
        for idx, scene in enumerate(script.get("scenes", []), start=1):
            out = work_dir / f"scene_{idx:02d}.mp3"
            text = scene.get("narration", "").strip()
            if not text:
                self._write_silent_wav(work_dir / f"scene_{idx:02d}.wav", duration_sec=2)
                out = work_dir / f"scene_{idx:02d}.wav"
            elif self._try_gtts(text, out):
                pass
            else:
                wav = work_dir / f"scene_{idx:02d}.wav"
                duration = max(2, int(scene.get("duration_sec", 8)))
                self._write_silent_wav(wav, duration_sec=duration)
                out = wav
            audio_paths.append(out)
        return audio_paths

    def _try_gtts(self, text: str, out_path: Path) -> bool:
        try:
            from gtts import gTTS

            gTTS(text=text, lang="en").save(str(out_path))
            return out_path.exists() and out_path.stat().st_size > 0
        except Exception as exc:  # noqa: BLE001
            logger.warning("gTTS unavailable, using silent audio fallback: %s", exc)
            return False

    @staticmethod
    def _write_silent_wav(path: Path, duration_sec: int) -> None:
        sample_rate = 44100
        n_frames = sample_rate * duration_sec
        with wave.open(str(path), "w") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(struct.pack("<h", 0) * n_frames)
