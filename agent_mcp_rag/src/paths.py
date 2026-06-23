from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DIR = DATA_DIR / "chroma"
MOCK_HISTORY_PATH = DATA_DIR / "mock_chat_history.json"

ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
SCENES_DIR = ARTIFACTS_DIR / "scenes"
PDF_DIR = ARTIFACTS_DIR / "pdf"
FINAL_PLAN_DIR = PROJECT_ROOT / "final_plan"


def run_scenes_dir(work_id: str) -> Path:
    return SCENES_DIR / work_id


def run_pdf_dir(work_id: str) -> Path:
    return PDF_DIR / work_id
