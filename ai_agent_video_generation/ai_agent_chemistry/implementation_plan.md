# AI Chemistry Backend Challenge - Implementation Plan

## 1) Goal and Scope

Build a backend-only FastAPI service where a client:

1. Requests a chemistry explanation video for one of three required queries.
2. Receives a job ID immediately.
3. Polls job status until completed or failed.
4. Retrieves video artifact metadata and file URL/path when complete.

Required supported queries:

- `How does the pH scale work?`
- `Why do atoms form covalent bonds?`
- `What is the difference between ionic and covalent bonding?`

Out of scope for this challenge:

- Frontend UI
- Real-time streaming playback service at scale
- Full production infra

## 2) Timeboxed Execution Plan (90-120 min)

### Phase A - Planning and design (20 min)

- Define API contract and job state machine.
- Decide artifact format and storage layout.
- Define async worker approach and reliability guardrails.
- Define what will be mocked vs real.

### Phase B - Minimal vertical slice (35 min)

- Implement FastAPI app skeleton.
- Add POST create-job endpoint.
- Add GET job endpoint and GET jobs list endpoint.
- Add background processing pipeline that creates artifacts.

### Phase C - Reliability and quality (25 min)

- Add input validation for only 3 required queries.
- Add retries/fallback path.
- Add deterministic content templates + output checks.
- Add structured logging and error handling.

### Phase D - Test and demo prep (20-40 min)

- Add tests for job lifecycle and API contract.
- Generate 3 final video artifacts for required queries.
- Write README + architecture note + walkthrough instructions.

## 3) Architecture Blueprint

Use clean boundaries so components can be swapped later.

### Layers

1. `api/` - FastAPI routers and schemas.
2. `domain/` - Job model, state transitions, validation rules.
3. `services/` - Video generation orchestration logic.
4. `repositories/` - Job persistence abstraction.
5. `artifacts/` - File storage abstraction for generated outputs.
6. `workers/` - Async/background execution runner.

### Suggested file structure

```text
app/
  main.py
  api/
    routes_jobs.py
    schemas.py
  domain/
    models.py
    states.py
    errors.py
  services/
    generation_service.py
    chemistry_content_service.py
    reliability_service.py
  repositories/
    job_repository.py
    in_memory_job_repository.py
  artifacts/
    artifact_store.py
    local_file_artifact_store.py
  workers/
    job_runner.py
  core/
    config.py
    logging.py
tests/
  test_jobs_api.py
  test_generation_pipeline.py
artifacts/
  videos/
  manifests/
docs/
  architecture_note.md
```

## 4) API Design (Clear and Demo-Friendly)

### POST `/v1/video-requests`

Request:

```json
{
  "query": "How does the pH scale work?"
}
```

Response (`202 Accepted`):

```json
{
  "job_id": "uuid",
  "status": "queued",
  "accepted_query": "How does the pH scale work?",
  "created_at": "ISO8601"
}
```

Behavior:

- Validate input query against supported list.
- Persist job with `queued`.
- Trigger async background job.

### GET `/v1/video-requests/{job_id}`

Response example:

```json
{
  "job_id": "uuid",
  "query": "How does the pH scale work?",
  "status": "completed",
  "created_at": "...",
  "started_at": "...",
  "completed_at": "...",
  "error": null,
  "artifact": {
    "video_path": "artifacts/videos/<job_id>.mp4",
    "manifest_path": "artifacts/manifests/<job_id>.json",
    "duration_sec": 48,
    "cost_estimate_usd": 0.03
  }
}
```

### GET `/v1/video-requests`

Purpose:

- List all jobs with latest statuses.
- Useful for observability and demo.

### GET `/v1/video-requests/{job_id}/artifact`

Purpose:

- Return downloadable/servable video file.
- For local demo, use `FileResponse`.

## 5) Domain Model and State Machine

### Job entity

Fields:

- `job_id`
- `query`
- `status` (`queued|running|completed|failed`)
- `attempt_count`
- timestamps (`created_at`, `started_at`, `completed_at`)
- `error`
- `artifact_metadata`
- `cost_estimate_usd`

### Valid transitions

- `queued -> running`
- `running -> completed`
- `running -> failed`

Reject illegal transitions to prevent inconsistent state.

## 6) Generation Pipeline Design

Pipeline steps:

1. **Normalize query**: map exact required query variants to canonical key.
2. **Build script**: produce short educational script (template-based + optional LLM).
3. **Build visual plan**: scene list (title, bullets, transitions, timing).
4. **Render visuals**: simple slide/animation frames.
5. **Generate audio**: TTS or mocked narration.
6. **Mux video + audio**: create final mp4.
7. **Validate output**: non-empty file, min duration, includes key terms.
8. **Persist artifact metadata** and mark complete.

For challenge speed/reliability: keep script generation deterministic using curated templates for the 3 required topics, then optionally enrich with LLM.

## 7) Reliability, Guardrails, and Non-Determinism Strategy

Use explicit safeguards:

1. **Input allowlist** for only required 3 queries.
2. **Template-first generation** to avoid random quality collapse.
3. **Output validation checks**:
   - file exists
   - duration range (e.g., 30-90s)
   - transcript contains expected concept keywords
4. **Retry policy**:
   - up to 2 retries on transient failures
   - exponential backoff (`1s`, `2s`)
5. **Fallback mode**:
   - if LLM step fails, use static curated explanation template.
6. **Structured errors** with failure reason categories:
   - `validation_error`, `generation_error`, `render_error`, `storage_error`
7. **Idempotency**:
   - if same `job_id` reruns, avoid duplicate artifact corruption.

## 8) Cost-Efficiency Plan

Track and expose approximate per-job cost:

- `script_generation_cost_usd`
- `tts_cost_usd`
- `render_compute_cost_usd` (estimated)
- `total_cost_usd`

Cost optimization choices:

- Use short scripts (45-60s).
- Reuse static assets/templates.
- Generate at moderate resolution for demo.
- Use local/offline tools where possible.
- Avoid unnecessary multiple LLM calls.

Document assumptions clearly in `architecture_note.md`.

## 9) Persistence and Artifact Boundaries

### Persistence

For challenge: in-memory repository with interface abstraction.

Upgrade path:

- Swap repository implementation to SQLite/Postgres without touching API/service layer.

### Artifacts

Store locally under:

- `artifacts/videos/`
- `artifacts/manifests/`

Manifest includes:

- input query
- generated script
- scene plan
- timing
- cost estimate
- generation version

## 10) Implementation Sequence (Detailed)

1. Create project skeleton and dependency setup (`FastAPI`, `uvicorn`, optional video libs).
2. Implement domain models + enums.
3. Implement repository interface + in-memory adapter.
4. Implement artifact store interface + local-file adapter.
5. Implement generation service with deterministic templates for 3 topics.
6. Implement worker/runner function that transitions states safely.
7. Implement API routes and schemas.
8. Wire app startup config and dependency injection.
9. Add logging middleware and exception handlers.
10. Add tests (API + pipeline).
11. Run manual demo with 3 required queries.
12. Commit generated videos and docs.

## 11) Test Plan

### Unit tests

- Query validation accepts only required 3 queries.
- State transitions reject invalid moves.
- Retry/fallback logic executes as expected.

### Integration/API tests

- Create job returns `202` + `job_id`.
- Polling endpoint eventually reaches `completed` or clear `failed`.
- Artifact endpoint returns file for completed job.
- List endpoint shows all submitted jobs and statuses.

### Reliability checks (manual)

- Repeat same query 3 times and compare quality consistency.
- Force a synthetic error and verify failed state + reason.
- Confirm retries and fallback behavior in logs.

## 12) Observability and Debugging

Add per-job logs with `job_id` correlation:

- `job_queued`
- `job_started`
- `generation_step_*`
- `job_completed`
- `job_failed`

Expose optional lightweight debug endpoint:

- GET `/v1/health`
- GET `/v1/metrics` (optional simple counters)

## 13) Deliverables Checklist (Submission Ready)

- [ ] FastAPI backend codebase.
- [ ] README with setup/run/API/test commands.
- [ ] Architecture note with lifecycle and boundaries.
- [ ] Demo walkthrough video/API run covering 3 required queries.
- [ ] 3 best generated video files committed.
- [ ] Mapping from each required query to generated video artifact.
- [ ] GitHub access granted to required emails.
- [ ] Zip file of final project.
- [ ] Google Drive recording link (full screen + face).

## 14) Suggested README Sections

1. Project Overview
2. Architecture Summary
3. Prerequisites
4. Setup
5. Run Service
6. API Endpoints
7. Run Tests
8. Generation Pipeline + Reliability Strategy
9. Cost Estimate Method
10. Known Limitations and Future Improvements

## 15) Risks and Mitigations

- **Risk**: video rendering toolchain instability on local machine.
  - **Mitigation**: keep fallback path that generates a simpler artifact (e.g., slideshow + TTS) and still fulfills contract.
- **Risk**: non-deterministic LLM content quality.
  - **Mitigation**: template-first content with controlled post-processing.
- **Risk**: unclear state when failures happen mid-pipeline.
  - **Mitigation**: explicit state transitions + structured error fields.

## 16) Stretch Goals (Only if time remains)

- Add deduplication cache for identical queries.
- Add job cancellation endpoint.
- Add simple queue backend abstraction.
- Add richer visual animations and better voice quality.
- Add OpenAPI examples for all endpoints.

## 17) Practical Demo Script (5-8 minutes)

1. Start API server.
2. Submit each of the 3 required queries via curl/Postman.
3. Show immediate `queued` responses with job IDs.
4. Poll statuses until complete.
5. Open artifact endpoint for each generated video.
6. Show job list endpoint with lifecycle history.
7. Explain cost/performance/reliability decisions briefly.

---

Use this plan as your execution checklist. If helpful, next step is to scaffold files exactly matching the architecture above and implement a minimal working vertical slice first.
