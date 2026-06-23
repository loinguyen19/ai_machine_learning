import sys
from pathlib import Path

# Imports use: ai_agent_video_generation.ai_agent_chemistry.app...
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
