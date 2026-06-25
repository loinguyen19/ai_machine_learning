<p align="center">
  <img src="assets/readme-cover.png" alt="AI Chemistry Video Request Service — agentic AI video generation" width="100%">
</p>

# AI Chemistry Video Request Service

Backend prototype for asynchronous chemistry explainer video requests using FastAPI.

**Repo context:** This is **project #2** in the [`agentic_ai`](../../README.md) collection. Recommended exploration order: #1 [Holiday Planner](../../agent_mcp_rag/README.md) → **#2 this project** → #3 [LangChain agent with tools](../../agent_with_tools/).

## How this project fits

| # | Project | Relationship to this service |
|---|---------|------------------------------|
| 1 | `agent_mcp_rag` | Same agentic mindset: tools, external APIs, and **artifacts on disk** (scenes, PDF). The holiday planner runs as a LangChain agent + MCP server; this project wraps a generation pipeline behind a REST API. |
| 2 | **This project** | Async job API: script → slides → narration → MP4, with manifests, guardrails, and cost tracking under `artifacts/`. |
| 3 | `agent_with_tools` | Minimal LangChain + Tavily example — the tool-calling pattern that #1 scales up via MCP. |

See [How the projects relate](../../README.md#how-the-projects-relate) in the root README for the conceptual stack diagram (#3 → #1 → #2).

## Quick Start

Virtual environment lives in the **parent folder**: `ai_agent_video_generation/.venv`.

```bash
cd ai_agent_video_generation/ai_agent_chemistry
make install
source ../.venv/bin/activate
make run-api
```

Open API docs at `http://localhost:8000/docs`.

You can also run the same targets from `ai_agent_video_generation/`:

```bash
cd ai_agent_video_generation
make install
make run-api
```

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
make test
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Create `../.venv` and install `requirements.txt` |
| `make activate` | Print `source ../.venv/bin/activate` |
| `make run-api` | Start FastAPI with reload on port 8000 |
| `make test` | Run `pytest` |
| `make reinstall` | Remove `.venv` and install fresh |
| `make clean-venv` | Remove `ai_agent_video_generation/.venv` |

## Project Structure

See `ARCHITECTURE.md` for lifecycle diagrams and boundaries.

## Known Limitations

- Prototype is single-process and in-memory (no DB/queue broker).
- gTTS requires network; offline runs use silent WAV fallback.
- LLM script generation is stubbed/documented, not fully wired in MVP.
