# AI Chemistry Video Request Service

Backend prototype for asynchronous chemistry explainer video requests using FastAPI.

## Quick Start

```bash
cd ai_agent_chemistry
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run API:

```bash
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open API docs at `http://localhost:8000/docs`.

## How To Play Generated Videos

**Why old videos did not play:** previous runs wrote the literal text `placeholder-mp4` (15 bytes) when `ffmpeg` was missing. That is not a valid MP4.

After this fix, the pipeline:

1. renders PNG slides (`Pillow`)
2. synthesizes narration (`gTTS`, with silent-audio fallback offline)
3. assembles a real MP4 via `ffmpeg` (system install) or bundled `imageio-ffmpeg`

### Option A — download from API

```bash
curl -X POST localhost:8000/v1/videos \
  -H "Content-Type: application/json" \
  -d '{"query":"How does the pH scale work?","topic":"chemistry"}'

# poll until status=completed
curl localhost:8000/v1/videos/<job_id>

curl -OJ localhost:8000/v1/videos/<job_id>/artifact
open ./<job_id>.mp4   # macOS QuickTime
```

### Option B — open local artifact directly

```bash
open artifacts/videos/<job_id>.mp4
```

If playback still fails, install ffmpeg:

```bash
brew install ffmpeg
# or rely on pip package imageio-ffmpeg (already in requirements.txt)
```

## Observe Job State / Logs

Each job now stores an `events` array (also written into the manifest JSON).

```bash
curl localhost:8000/v1/videos/<job_id> | jq '.events'
```

Server logs also print structured lines:

```text
job=<id> status=generating_media step=generating_media Synthesizing narration audio
```

## Evaluate Success Metrics

```bash
curl localhost:8000/v1/videos/<job_id>/evaluation
```

This scores the job against: helpful, consistent, guardrails, explainable, cost-efficient, reliable, educational.

## API Endpoints

- `POST /v1/videos` - create async generation job
- `GET /v1/videos` - list jobs
- `GET /v1/videos/{job_id}` - get job status/details + events
- `GET /v1/videos/{job_id}/artifact` - download completed MP4
- `GET /v1/videos/{job_id}/evaluation` - quality/cost/reliability report
- `GET /health` - liveness check

## Required Queries

- `How does the pH scale work?`
- `Why do atoms form covalent bonds?`
- `What is the difference between ionic and covalent bonding?`

## Generation Stack & Cost

| Step | Provider | Cost |
|------|----------|------|
| Script | Template (default) | $0 |
| Script | LLM optional (`USE_LLM_SCRIPT=1`) | ~$0.001–0.01 |
| Slides | Pillow PNG renderer | $0 |
| Audio | gTTS | $0 |
| Video | ffmpeg / imageio-ffmpeg | $0 |

Cost is computed in `app/generation/cost_calculator.py` and stored per job as `artifact.cost_estimate_usd` + `cost_breakdown`.

## Guardrails (where they live)

- Query allowlist: `app/generation/validators.py` (`validate_query`)
- Script relevance keywords: `validate_script`
- Bounded retries + fallback templates: `app/services/video_worker.py`
- Structured failure fields: `failed_step`, `error_code`, `error_message`

## Why template-first scripts (not LLM by default)?

For the 90–120 minute challenge scope with exactly 3 fixed queries:

- **Reliability:** templates always pass validation; LLM JSON can fail or drift off-topic
- **Cost:** $0 vs cents per call
- **Consistency:** repeatable demos for reviewers

LLM integration is intentionally behind a provider boundary (`ScriptGenerator`) and can be enabled later with `USE_LLM_SCRIPT=1` while keeping templates as fallback.

## Tests

```bash
PYTHONPATH=. pytest -q tests
```

## Project Structure

See `ARCHITECTURE.md` for lifecycle diagrams and boundaries.

## Known Limitations

- Prototype is single-process and in-memory (no DB/queue broker).
- gTTS requires network; offline runs use silent WAV fallback.
- LLM script generation is stubbed/documented, not fully wired in MVP.
