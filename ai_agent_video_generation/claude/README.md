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