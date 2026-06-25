<p align="center">
  <img src="assets/readme-cover.png" alt="Agentic AI — LLM applications, MCP, RAG, and production Python backends" width="100%">
</p>

# Agentic AI

A collection of personal projects exploring **agentic AI**, **LLM applications**, and **production-style Python backends**. Each project is self-contained with its own virtual environment, dependencies, and documentation.

The repo includes three projects at increasing scope: a flagship **Holiday Planner** (MCP + RAG), an **async video-generation API**, and a minimal **LangChain + tools** starter.

**Recommended quick start order:** #1 Holiday Planner → #2 Chemistry Video → #3 LangChain agent.

---

## Projects

| # | Project | What it does | Stack highlights |
|---|---------|--------------|------------------|
| 1 | [`agent_mcp_rag/`](agent_mcp_rag/) | Holiday planning assistant: brief → personalized itinerary, scene previews, PDF deliverable | LangChain ReAct, FastMCP, Chroma RAG, Tavily, fpdf2 |
| 2 | [`ai_agent_video_generation/ai_agent_chemistry/`](ai_agent_video_generation/ai_agent_chemistry/) | Async API that turns chemistry questions into narrated explainer videos | FastAPI, Pillow, gTTS, ffmpeg |
| 3 | [`agent_with_tools/`](agent_with_tools/) | Search agent: answers client questions via LangChain ReAct + Tavily web search | LangChain, Tavily, Gemini |

For architecture diagrams, API references, and output paths, see each project's README.

---

## Repository layout

```text
agentic_ai/
├── README.md                          # this file
├── agent_mcp_rag/                     # #1 Holiday Planner (MCP + RAG)
│   ├── README.md
│   ├── Makefile
│   ├── requirements.txt
│   ├── data/                          # mock chat history + Chroma store
│   ├── artifacts/                     # per-run archives (generated)
│   ├── final_plan/                    # latest deliverable (generated)
│   └── src/
│       ├── agent.py
│       ├── server.py                  # MCP server
│       ├── rag/
│       └── planner/
├── ai_agent_video_generation/
│   ├── Makefile                       # delegates to chemistry subproject
│   ├── .venv/                         # shared venv for video projects
│   └── ai_agent_chemistry/            # #2 Chemistry Video API
│       ├── README.md
│       ├── ARCHITECTURE.md
│       ├── Makefile
│       └── app/
└── agent_with_tools/                  # #3 LangChain agent + Tavily tool
    ├── requirements.txt
    └── src/agent.py
```

---

## Prerequisites

- **Python 3.11+**
- **API keys** (per project — see below)
- **ffmpeg** (recommended for chemistry video playback): `brew install ffmpeg` on macOS

Each project uses its **own** `.venv`. There is no shared root virtual environment.

---

## Quick start by project

### 1. Holiday Planner Agent (MCP + RAG)

Turns a short client brief into a trip plan with RAG-backed preferences, Tavily research, destination scene cards, and a PDF.

```bash
cd agent_mcp_rag
make install
source .venv/bin/activate
```

Create `agent_mcp_rag/.env`:

```env
OPEN_ROUTER_AI_API_KEY=your_openrouter_key
TAVILY_API_KEY=your_tavily_key
```

Optional — use Google Gemini instead:

```env
LLM_PROVIDER=google
GOOGLE_API_KEY=your_gemini_key
LLM_MODEL=gemini-2.5-flash
```

Seed mock client memory (first run; also auto-seeds when Chroma is empty):

```bash
make seed-memory
```

Run the agent:

```bash
make run-agent
```

**Outputs:** latest plan at `agent_mcp_rag/final_plan/`; per-run archives under `artifacts/`.

Full setup, MCP tool reference, and example brief: [`agent_mcp_rag/README.md`](agent_mcp_rag/README.md).

| Makefile target | Description |
|-----------------|-------------|
| `make install` | Create `.venv` and install dependencies |
| `make seed-memory` | Load mock chat history into Chroma |
| `make run-agent` | Run the holiday planner |
| `make clean` | Remove generated `data/chroma`, `artifacts/`, `final_plan/` |
| `make help` | List all targets |

---

### 2. AI Chemistry Video API

Async FastAPI service that accepts a chemistry question and produces an MP4 explainer (slides + narration).

```bash
cd ai_agent_video_generation/ai_agent_chemistry
make install
source ../.venv/bin/activate
make run-api
```

Or from the parent folder:

```bash
cd ai_agent_video_generation
make install
make run-api
```

Open interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

Example request:

```bash
curl -X POST localhost:8000/v1/videos \
  -H "Content-Type: application/json" \
  -d '{"query":"How does the pH scale work?","topic":"chemistry"}'

curl localhost:8000/v1/videos/<job_id>
curl -OJ localhost:8000/v1/videos/<job_id>/artifact
```

Run tests:

```bash
make test
```

Full API reference, playback notes, and cost breakdown: [`ai_agent_video_generation/ai_agent_chemistry/README.md`](ai_agent_video_generation/ai_agent_chemistry/README.md).

| Makefile target | Description |
|-----------------|-------------|
| `make install` | Create `ai_agent_video_generation/.venv` |
| `make run-api` | Start FastAPI on port 8000 (reload) |
| `make test` | Run pytest suite |
| `make help` | List all targets |

---

### 3. LangChain Search Agent

A ReAct agent with a Tavily `web_search` tool — answers client questions in interactive or single-shot mode.

```bash
cd agent_with_tools
make install
source .venv/bin/activate
make run-agent
```

Create `agent_with_tools/.env` (see `.env.example`):

```env
TAVILY_API_KEY=your_tavily_key
GOOGLE_API_KEY=your_gemini_key
```

Single question:

```bash
cd src && python agent.py "What is the capital of France?"
```

Full setup and configuration: [`agent_with_tools/README.md`](agent_with_tools/README.md).

| Makefile target | Description |
|-----------------|-------------|
| `make install` | Create `.venv` and install dependencies |
| `make run-agent` | Run interactive search agent |
| `make help` | List all targets |

---

## Environment variables (summary)

| # | Project | Required | Optional |
|---|---------|----------|----------|
| 1 | `agent_mcp_rag` | `OPEN_ROUTER_AI_API_KEY` (or `GOOGLE_API_KEY` with `LLM_PROVIDER=google`), `TAVILY_API_KEY` | `LLM_MODEL`, `CLIENT_ID`, `WORK_ID` |
| 2 | `ai_agent_chemistry` | None for template-based generation | `USE_LLM_SCRIPT=1` for optional LLM scripts; see `.env.example` |
| 3 | `agent_with_tools` | `TAVILY_API_KEY`, `GOOGLE_API_KEY` | — |

Never commit `.env` files or API keys. They are listed in `.gitignore`.

---

## How the projects relate

The **quick start order** (#1 → #2 → #3) is the recommended way to explore the repo: start with the full Holiday Planner, then the video API, then the minimal LangChain script.

The diagram below is a **conceptual stack** — how ideas build on each other — not the order you run them:

```mermaid
flowchart LR
    P3["#3 LangChain + tools<br/>agent_with_tools"] -->|tool-calling foundation| P1["#1 Holiday Planner<br/>agent_mcp_rag"]
    P1 -->|MCP + RAG + artifacts + media| P2["#2 Chemistry Video<br/>ai_agent_chemistry"]
    P2 -->|REST API + async jobs + guardrails| D[Production patterns]
```

| # | Project | Role in the stack |
|---|---------|-------------------|
| **1** | `agent_mcp_rag` | Flagship agent: MCP tool server, Chroma RAG memory, Tavily search, structured deliverables (JSON, Markdown, PDF, scene images). |
| **2** | `ai_agent_chemistry` | Service layer: same artifact mindset as #1, but exposed as FastAPI with background jobs, manifests, and evaluation. |
| **3** | `agent_with_tools` | Smallest slice: LangChain agent + one Tavily tool — the pattern that #1 extends into a full MCP workflow. |

**Quick start vs diagram:** run **#1 → #2 → #3** to see the most complete projects first; read the diagram **#3 → #1 → #2** to understand how complexity grows from basic tool-calling to a deployable API.

---

## Generated artifacts

These paths are created at runtime and are typically gitignored or cleaned via Make targets:

| Path | Project | Contents |
|------|---------|----------|
| `agent_mcp_rag/final_plan/` | Holiday Planner | Latest PDF, JSON, Markdown, scene images |
| `agent_mcp_rag/artifacts/` | Holiday Planner | Per-run scene and PDF archives |
| `agent_mcp_rag/data/chroma/` | Holiday Planner | Chroma vector store |
| `ai_agent_chemistry/artifacts/` | Chemistry Video | MP4s, manifests, intermediate slides/audio |

---

## License

See [LICENSE](LICENSE).
