#!/usr/bin/env bash
cd "$(dirname "$0")"

# Terminal 1 — run server
uvicorn app.main:app --reload

# Terminal 2 — submit all three required concepts
# curl -X POST http://localhost:8000/videos/request \
#   -H "Content-Type: application/json" \
#   -d '{"concept": "How does the pH scale work?"}'
#
# curl http://localhost:8000/videos/jobs/{job_id}
# curl -o ph_scale.mp4 http://localhost:8000/videos/jobs/{job_id}/download
# curl http://localhost:8000/videos/jobs
