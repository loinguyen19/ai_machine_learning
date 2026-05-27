# AI Chemistry Video Request Service

Backend prototype for asynchronous chemistry explainer video requests using FastAPI.

This implementation supports exactly the three required challenge queries, exposes job lifecycle APIs, and produces local video artifacts with manifest metadata.

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

## API Endpoints

- `POST /v1/videos` - create async generation job
- `GET /v1/videos` - list jobs
- `GET /v1/videos/{job_id}` - get job status/details
- `GET /v1/videos/{job_id}/artifact` - download completed video artifact
- `GET /health` - liveness check

## Required Queries

- `How does the pH scale work?`
- `Why do atoms form covalent bonds?`
- `What is the difference between ionic and covalent bonding?`

## Example Flow

```bash
curl -X POST localhost:8000/v1/videos \
  -H "Content-Type: application/json" \
  -d '{"query":"How does the pH scale work?","topic":"chemistry"}'

curl localhost:8000/v1/videos/<job_id>
curl -O localhost:8000/v1/videos/<job_id>/artifact
```

## Reliability Features

- Query allowlist validation for required challenge scope.
- Structured status transitions from `queued` to terminal states.
- Bounded retries in worker loop.
- Script relevance validation against query-specific terms.
- Deterministic fallback scripts for required concepts.
- Structured failure fields (`failed_step`, `error_code`, `error_message`).

## Cost/Quality Approach

- Template-first script generation for consistency and low cost.
- Deterministic media pipeline with provider boundaries.
- Estimated cost metadata tracked per job (`cost_estimate_usd`).
- Local assembly path uses ffmpeg when available and safe placeholder fallback when unavailable.

## Tests

Run:

```bash
PYTHONPATH=. pytest -q tests
```

Current suite covers:

- job creation API behavior
- unknown job handling
- invalid query failure behavior
- generation pipeline with mocked assembler

## Project Structure

See `ARCHITECTURE.md` for lifecycle diagrams and boundaries.

Core app is under `app/`:

- `api/` routes and schemas
- `domain/` models/exceptions
- `services/` orchestration and worker
- `generation/` pipeline + providers + validators
- `persistence/` repository boundary and in-memory adapter
- `storage/` artifact handling

## Artifacts

- Generated artifacts: `artifacts/videos/` and `artifacts/manifests/`
- Committed submission outputs: `submissions/`

## Known Limitations

- Prototype is single-process and in-memory (no DB/queue broker).
- Placeholder MP4 fallback is used when ffmpeg is unavailable.
- LLM/TTS vendors are represented as swappable interfaces, not full provider integrations.
