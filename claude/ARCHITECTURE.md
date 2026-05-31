Cover these four sections clearly:
Job Lifecycle: Describe the PENDING → PROCESSING → COMPLETED/FAILED state machine and what triggers each transition.
Persistence Boundary: State explicitly that JobStore is an in-memory singleton with a clean interface — swapping it for PostgreSQL/Redis requires only replacing that class.
Generation Boundary: Describe that pipeline.py orchestrates four swappable modules. Each module (script, slides, audio, video) is independently replaceable — e.g., swap gTTS for ElevenLabs, swap matplotlib slides for a real animation engine.
Cost Model: ~$0.003–0.005 per video (Claude Sonnet API). Compare to Runway ML (~$0.50–$2.00) or Sora to justify the approach.
