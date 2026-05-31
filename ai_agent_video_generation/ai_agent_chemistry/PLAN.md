# PLAN - AI Chemistry Video Request Service

## In Scope (MVP)

- FastAPI backend with asynchronous video request jobs.
- End-to-end support for exactly three required chemistry queries.
- Downloadable/streamable video artifact per completed job.
- Job status lifecycle visibility (`queued` to terminal states).
- List and inspect jobs through API.

## Explicitly Out of Scope

- Frontend UI.
- Authentication/authorization.
- Multi-tenant infrastructure and billing.
- Cloud deployment setup.
- Arbitrary chemistry and non-chemistry subject support.

## Fake vs Real

### Real in this implementation

- API contracts and status lifecycle.
- Repository boundary for persistence.
- Artifact storage boundary.
- Async worker orchestration.
- Generation pipeline boundary and provider interfaces.
- Validation, retries, fallback path, and structured failures.

### Intentionally simplified/mockable

- LLM script quality (template-first with optional provider swap).
- Advanced visuals (slide-based frames instead of complex generated animation).
- TTS provider (local fallback where needed).

## API Sketch

- `POST /v1/videos` - create job from `query` and optional `topic`.
- `GET /v1/videos` - list jobs, optional status filter.
- `GET /v1/videos/{job_id}` - get job detail and artifact metadata.
- `GET /v1/videos/{job_id}/artifact` - serve completed MP4.
- `GET /health` - basic service liveness.

## Time Split (90-120 min target)

- 15 min - plan and API contract.
- 25 min - project skeleton and domain/repository.
- 25 min - routes, async runner, status transitions.
- 20 min - generation pipeline + reliability checks.
- 15 min - tests and docs polish.
- 10+ min - manual run for three required queries.

## Session Success Criteria

- All required three queries complete at least once.
- Failed runs produce explicit terminal error state, not hanging jobs.
- README explains architecture boundaries, reliability strategy, and cost estimate.
