# AI Chemistry Video Request Service — Full Implementation Guide

## 1. Strategic Planning (Before Writing a Line of Code)

### What to Build vs. Fake vs. Skip

| Aspect | Decision | Rationale |
|---|---|---|
| FastAPI backend | Build fully | Core requirement |
| Async job queue | Build (in-memory with `asyncio`) | Clean boundary, no Redis needed |
| Video generation | **Partially real** — use Claude API for script + matplotlib/PIL for visuals + gTTS for audio, then stitch with MoviePy | Cheapest real pipeline; no Sora/Runway cost |
| Database | In-memory dict + local file store | Acceptable per spec, keep boundary clean |
| Frontend | Skip entirely | Explicitly excluded |
| Auth | Skip | Not mentioned, don't gold-plate |
| Other STEM topics | Design for, don't implement | Spec says "make it clear how they'd be added" |

### Cost Strategy (Critical — They Evaluate This)

The cheapest real pipeline that produces coherent visual + audio video:
- **Claude Sonnet** → generate structured script + slide content (~$0.003/video)
- **gTTS (Google Text-to-Speech, free)** or **ElevenLabs (paid)** → narration audio
- **Matplotlib** → render text/diagram slides as PNG frames (free)
- **MoviePy** → stitch frames + audio into MP4 (free)

**Total cost per video: ~$0.003–0.01** vs. Runway/Sora ($0.50–$5.00+)

---

## 2. Architecture

### Job Lifecycle State Machine

```
PENDING → PROCESSING → COMPLETED
                    ↘ FAILED (with retry logic)
```

### Directory Structure

```
chemistry-video-service/
├── app/
│   ├── main.py                  # FastAPI app, routes
│   ├── models.py                # Pydantic schemas
│   ├── job_store.py             # In-memory job registry (clean boundary)
│   ├── routers/
│   │   └── videos.py            # All /videos endpoints
│   └── generation/
│       ├── pipeline.py          # Orchestrates the full generation flow
│       ├── script_generator.py  # Claude API → structured script
│       ├── slide_renderer.py    # Matplotlib → PNG frames
│       ├── audio_generator.py   # gTTS → MP3 per slide
│       └── video_assembler.py   # MoviePy → final MP4
├── artifacts/                   # Generated MP4s stored here
├── tests/
│   ├── test_api.py
│   └── test_pipeline.py
├── requirements.txt
├── README.md
└── ARCHITECTURE.md
```

### API Design

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/videos/request` | Submit a concept request → returns `job_id` |
| `GET` | `/videos/jobs` | List all jobs with status |
| `GET` | `/videos/jobs/{job_id}` | Get status of one job |
| `GET` | `/videos/jobs/{job_id}/download` | Download/stream the MP4 when COMPLETED |

---

## 3. Implementation — Step by Step

### Step 1: Project Setup

```bash
mkdir chemistry-video-service && cd chemistry-video-service
python -m venv venv && source venv/bin/activate
pip install fastapi uvicorn anthropic gTTS moviepy matplotlib pillow pytest httpx python-dotenv
```

`requirements.txt` — pin versions for reproducibility.

`.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

### Step 2: Models (`app/models.py`)

```python
from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import datetime

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class VideoRequest(BaseModel):
    concept: str  # e.g. "How does the pH scale work?"

class JobResponse(BaseModel):
    job_id: str
    concept: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    artifact_path: Optional[str] = None
    error_message: Optional[str] = None
    cost_estimate_usd: Optional[float] = None
```

---

### Step 3: Job Store (`app/job_store.py`)

This is the clean persistence boundary the spec is looking for:

```python
import uuid
from datetime import datetime
from typing import Dict, Optional
from app.models import JobResponse, JobStatus

class JobStore:
    def __init__(self):
        self._jobs: Dict[str, JobResponse] = {}

    def create_job(self, concept: str) -> JobResponse:
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        job = JobResponse(
            job_id=job_id,
            concept=concept,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobResponse]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[JobResponse]:
        return list(self._jobs.values())

    def update_status(self, job_id: str, status: JobStatus, **kwargs):
        job = self._jobs[job_id]
        updated = job.model_copy(update={"status": status, "updated_at": datetime.utcnow(), **kwargs})
        self._jobs[job_id] = updated
        return updated

# Singleton — in production, swap with a DB-backed implementation
job_store = JobStore()
```

---

### Step 4: Script Generator (`app/generation/script_generator.py`)

This is the most important generation piece. Prompt Claude to return **structured JSON** so the downstream renderer is deterministic:

```python
import anthropic
import json
from tenacity import retry, stop_after_attempt, wait_exponential

ALLOWED_CONCEPTS = {
    "how does the ph scale work",
    "why do atoms form covalent bonds",
    "what is the difference between ionic and covalent bonding",
}

def validate_concept(concept: str) -> bool:
    return concept.strip().lower() in ALLOWED_CONCEPTS

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_script(concept: str) -> dict:
    client = anthropic.Anthropic()
    
    prompt = f"""You are an educational video script writer for high school chemistry.
    
Generate a structured video script for the concept: "{concept}"

Return ONLY valid JSON in this exact format, no other text:
{{
  "title": "Short title for the video",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide title",
      "narration": "What the narrator says (2-4 sentences, clear and engaging)",
      "visual_elements": ["bullet point or diagram description"],
      "duration_seconds": 8
    }}
  ],
  "total_slides": 5
}}

Requirements:
- Exactly 5 slides
- Slide 1: Hook/introduction
- Slides 2-4: Core explanation with progressively deeper detail
- Slide 5: Summary and real-world application
- Each narration 2-4 sentences
- Visual elements: 2-4 bullet points or a simple diagram description per slide
- Keep language accessible for a 16-year-old learner
"""
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.content[0].text.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    script = json.loads(raw)
    
    # Validate structure
    assert "slides" in script and len(script["slides"]) == 5
    for slide in script["slides"]:
        assert "narration" in slide and "visual_elements" in slide
    
    return script
```

Key reliability engineering here: `tenacity` for retries, structural validation after parsing, and stripping markdown fences.

---

### Step 5: Slide Renderer (`app/generation/slide_renderer.py`)

Renders each slide as a 1280×720 PNG using matplotlib:

```python
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

BRAND_BG = "#0F1B2D"
BRAND_ACCENT = "#4FC3F7"
TEXT_COLOR = "#FFFFFF"
SUBTITLE_COLOR = "#B0BEC5"

def render_slide(slide: dict, output_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(12.8, 7.2), dpi=100)
    fig.patch.set_facecolor(BRAND_BG)
    ax.set_facecolor(BRAND_BG)
    ax.axis("off")
    
    # Accent bar at top
    ax.add_patch(patches.Rectangle((0, 0.92), 1, 0.08,
                                    transform=ax.transAxes,
                                    color=BRAND_ACCENT, zorder=2))
    
    # Slide number
    ax.text(0.97, 0.955, f"{slide['slide_number']}/5",
            transform=ax.transAxes, color=BRAND_BG,
            fontsize=11, ha="right", va="center", fontweight="bold")
    
    # Title
    ax.text(0.5, 0.82, slide["title"],
            transform=ax.transAxes, color=BRAND_ACCENT,
            fontsize=22, ha="center", va="top", fontweight="bold")
    
    # Visual elements (bullet points)
    y_pos = 0.68
    for element in slide["visual_elements"]:
        ax.text(0.1, y_pos, f"• {element}",
                transform=ax.transAxes, color=TEXT_COLOR,
                fontsize=14, ha="left", va="top", wrap=True,
                multialignment="left")
        y_pos -= 0.13
    
    plt.tight_layout(pad=0)
    fig.savefig(output_path, bbox_inches="tight", facecolor=BRAND_BG)
    plt.close(fig)
    return output_path
```

---

### Step 6: Audio Generator (`app/generation/audio_generator.py`)

```python
from gtts import gTTS
from pathlib import Path

def generate_narration(text: str, output_path: Path) -> Path:
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(str(output_path))
    return output_path
```

---

### Step 7: Video Assembler (`app/generation/video_assembler.py`)

```python
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from pathlib import Path
from typing import List

def assemble_video(slide_paths: List[Path], audio_paths: List[Path], output_path: Path) -> Path:
    clips = []
    for img_path, aud_path in zip(slide_paths, audio_paths):
        audio = AudioFileClip(str(aud_path))
        duration = audio.duration + 0.5  # small pause after each slide
        clip = ImageClip(str(img_path)).set_duration(duration).set_audio(audio)
        clips.append(clip)
    
    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(str(output_path), fps=24, codec="libx264",
                          audio_codec="aac", logger=None)
    return output_path
```

---

### Step 8: Pipeline Orchestrator (`app/generation/pipeline.py`)

```python
import asyncio
from pathlib import Path
from app.job_store import job_store
from app.models import JobStatus
from .script_generator import generate_script
from .slide_renderer import render_slide
from .audio_generator import generate_narration
from .video_assembler import assemble_video
import tempfile, shutil, logging

logger = logging.getLogger(__name__)
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

async def run_pipeline(job_id: str, concept: str):
    job_store.update_status(job_id, JobStatus.PROCESSING)
    tmp_dir = Path(tempfile.mkdtemp())
    
    try:
        # 1. Generate script (sync → run in thread pool to not block event loop)
        logger.info(f"[{job_id}] Generating script for: {concept}")
        script = await asyncio.get_event_loop().run_in_executor(
            None, generate_script, concept
        )
        
        slide_paths, audio_paths = [], []
        
        # 2. Render slides + audio per slide
        for slide in script["slides"]:
            n = slide["slide_number"]
            img_path = tmp_dir / f"slide_{n}.png"
            aud_path = tmp_dir / f"audio_{n}.mp3"
            
            render_slide(slide, img_path)
            await asyncio.get_event_loop().run_in_executor(
                None, generate_narration, slide["narration"], aud_path
            )
            slide_paths.append(img_path)
            audio_paths.append(aud_path)
        
        # 3. Assemble video
        output_path = ARTIFACTS_DIR / f"{job_id}.mp4"
        await asyncio.get_event_loop().run_in_executor(
            None, assemble_video, slide_paths, audio_paths, output_path
        )
        
        job_store.update_status(
            job_id, JobStatus.COMPLETED,
            artifact_path=str(output_path),
            cost_estimate_usd=0.005  # Claude API cost estimate
        )
        logger.info(f"[{job_id}] Completed successfully.")
        
    except Exception as e:
        logger.error(f"[{job_id}] Pipeline failed: {e}", exc_info=True)
        job_store.update_status(job_id, JobStatus.FAILED, error_message=str(e))
    
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
```

---

### Step 9: Router (`app/routers/videos.py`)

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.models import VideoRequest, JobResponse
from app.job_store import job_store
from app.generation.script_generator import validate_concept
from app.generation.pipeline import run_pipeline
from pathlib import Path

router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_CONCEPTS_MSG = (
    "Supported concepts: "
    "'How does the pH scale work?', "
    "'Why do atoms form covalent bonds?', "
    "'What is the difference between ionic and covalent bonding?'"
)

@router.post("/request", response_model=JobResponse, status_code=202)
async def request_video(body: VideoRequest, background_tasks: BackgroundTasks):
    if not validate_concept(body.concept):
        raise HTTPException(status_code=422, detail=f"Unsupported concept. {ALLOWED_CONCEPTS_MSG}")
    
    job = job_store.create_job(body.concept)
    background_tasks.add_task(run_pipeline, job.job_id, body.concept)
    return job

@router.get("/jobs", response_model=list[JobResponse])
def list_jobs():
    return job_store.list_jobs()

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/jobs/{job_id}/download")
def download_video(job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=409, detail=f"Job is {job.status}, not completed yet")
    
    path = Path(job.artifact_path)
    if not path.exists():
        raise HTTPException(status_code=500, detail="Artifact file missing")
    
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")
```

---

### Step 10: Main App (`app/main.py`)

```python
from fastapi import FastAPI
from app.routers.videos import router as videos_router
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Chemistry Video Request Service",
    description="Submit chemistry concept requests and receive AI-generated educational videos.",
    version="1.0.0",
)

app.include_router(videos_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

### Step 11: Tests (`tests/test_api.py`)

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, AsyncMock

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200

def test_request_invalid_concept():
    r = client.post("/videos/request", json={"concept": "explain quantum gravity"})
    assert r.status_code == 422

def test_request_valid_concept_returns_pending():
    with patch("app.routers.videos.run_pipeline", new_callable=AsyncMock):
        r = client.post("/videos/request", json={"concept": "How does the pH scale work?"})
    assert r.status_code == 202
    data = r.json()
    assert data["status"] == "pending"
    assert "job_id" in data

def test_list_jobs():
    r = client.get("/videos/jobs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_nonexistent_job():
    r = client.get("/videos/jobs/nonexistent-id")
    assert r.status_code == 404

def test_download_not_completed_job():
    with patch("app.routers.videos.run_pipeline", new_callable=AsyncMock):
        r = client.post("/videos/request", json={"concept": "Why do atoms form covalent bonds?"})
    job_id = r.json()["job_id"]
    r2 = client.get(f"/videos/jobs/{job_id}/download")
    assert r2.status_code == 409
```

---

## 4. Reliability Engineering (What Makes This Stand Out)

The spec explicitly calls out non-determinism handling. Make sure you address these:

| Risk | Mitigation |
|---|---|
| Claude returns malformed JSON | Strip markdown fences + `json.loads` in try/except + retry with `tenacity` |
| Claude returns wrong number of slides | Structural assertion post-parse triggers retry |
| gTTS network flake | Wrap in retry decorator |
| MoviePy crash on malformed audio | Validate audio file size before assembling |
| Job stuck in PROCESSING | Can add a timeout watchdog (mention in architecture even if not implemented) |

---

## 5. README.md Structure

```markdown
# Chemistry Video Request Service

## Setup
pip install -r requirements.txt
cp .env.example .env  # add ANTHROPIC_API_KEY

## Run
uvicorn app.main:app --reload

## API
POST /videos/request        {"concept": "How does the pH scale work?"}
GET  /videos/jobs           list all jobs
GET  /videos/jobs/{id}      get one job
GET  /videos/jobs/{id}/download  stream MP4

## Tests
pytest tests/ -v

## Supported Concepts
- "How does the pH scale work?"
- "Why do atoms form covalent bonds?"
- "What is the difference between ionic and covalent bonding?"
```

---

## 6. ARCHITECTURE.md — What to Write

Cover these four sections clearly:

**Job Lifecycle:** Describe the PENDING → PROCESSING → COMPLETED/FAILED state machine and what triggers each transition.

**Persistence Boundary:** State explicitly that `JobStore` is an in-memory singleton with a clean interface — swapping it for PostgreSQL/Redis requires only replacing that class.

**Generation Boundary:** Describe that `pipeline.py` orchestrates four swappable modules. Each module (script, slides, audio, video) is independently replaceable — e.g., swap gTTS for ElevenLabs, swap matplotlib slides for a real animation engine.

**Cost Model:** ~$0.003–0.005 per video (Claude Sonnet API). Compare to Runway ML (~$0.50–$2.00) or Sora to justify the approach.

---

## 7. Guiding Your AI Agent (Cursor/Claude Code)

When using Claude Code or Cursor, give it one module at a time with clear contracts:

> *"Implement `slide_renderer.py`. It takes a slide dict with keys `title`, `visual_elements` (list of strings), `slide_number` (int). It should return a 1280×720 PNG saved to the given Path. Use matplotlib with a dark theme. Here is the exact function signature: `def render_slide(slide: dict, output_path: Path) -> Path`"*

Then verify before moving on — run it, look at the PNG, fix if ugly. Don't let the agent chain 5 modules before you've validated each one.

---

## 8. Demo Script (for Your Recording)

```bash
# Terminal 1 — run server
uvicorn app.main:app --reload

# Terminal 2 — submit all three required concepts
curl -X POST http://localhost:8000/videos/request \
  -H "Content-Type: application/json" \
  -d '{"concept": "How does the pH scale work?"}'

# Poll for status
curl http://localhost:8000/videos/jobs/{job_id}

# Download when completed
curl -o ph_scale.mp4 http://localhost:8000/videos/jobs/{job_id}/download

# List all jobs
curl http://localhost:8000/videos/jobs
```

Show the MP4 playing in the recording. That's your demo.

---

## 9. What Separates a Good from Great Submission

- **Explain cost explicitly** in the architecture note — "each video costs ~$0.005, here's why"
- **Show the generation boundary clearly** — evaluators want to see you understand that `script_generator.py`, `slide_renderer.py` etc. are plug-in slots
- **Structured script output from Claude** (JSON schema) rather than free text — this is the single biggest reliability win
- **Don't over-engineer** — they said 90-120 minutes; a clean small thing beats a broken large thing
- **Commit the three actual MP4s** into the repo as required — don't forget this