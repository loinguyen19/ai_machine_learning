from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ArtifactStore:
    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir)
        self.videos = self.root / "videos"
        self.manifests = self.root / "manifests"
        self.videos.mkdir(parents=True, exist_ok=True)
        self.manifests.mkdir(parents=True, exist_ok=True)

    def video_path(self, job_id: str) -> Path:
        return self.videos / f"{job_id}.mp4"

    def manifest_path(self, job_id: str) -> Path:
        return self.manifests / f"{job_id}.json"

    def write_manifest(self, job_id: str, payload: dict[str, Any]) -> str:
        path = self.manifest_path(job_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)
