# Submission Checklist

## Completed in Repository

- FastAPI backend and async job flow implemented.
- Architecture note included (`ARCHITECTURE.md`).
- Setup/run/API/test docs included (`README.md`).
- Three required query artifacts generated in `submissions/` with sidecar query files.

## Manual Final Steps (outside local code changes)

1. Record demo walkthrough video:
   - start server
   - submit each required query
   - poll status and retrieve artifacts
2. Upload full session recording (screen + face) to Google Drive.
3. Push repo to GitHub and add read access:
   - `praveen.k@growtrics.ai`
   - `tech@growtrics.ai`
4. Create zip bundle for submission:

```bash
cd ..
zip -r ai_agent_chemistry_submission.zip ai_agent_chemistry -x "ai_agent_chemistry/.venv/*"
```

5. Share:
   - GitHub repository link
   - zip file
   - Drive link to full recording

## Quick Demo Commands

```bash
cd ai_agent_chemistry
source .venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
curl -X POST localhost:8000/v1/videos -H "Content-Type: application/json" \
  -d '{"query":"How does the pH scale work?","topic":"chemistry"}'
```
