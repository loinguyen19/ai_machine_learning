#!/usr/bin/env bash
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