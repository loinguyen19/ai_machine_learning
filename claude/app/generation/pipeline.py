import asyncio
from pathlib import Path
from app.job_store import job_store
from app.models import JobStatus
from .script_generator import generate_script, generate_script_with_ollama
from .slide_renderer import render_slide
from .audio_generator import generate_narration
from .video_assembler import assemble_video
import tempfile, shutil, logging

logger = logging.getLogger(__name__)
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

async def run_pipeline(job_id: str, concept: str):
    job_store.update_status(job_id, JobStatus.PROCESSING)
    tmp_dir = Path(tempfile.mkdtemp())
    
    try:
        # 1. Generate script (sync → run in thread pool to not block event loop)
        logger.info(f"[{job_id}] Generating script for: {concept}")
        script = await asyncio.get_event_loop().run_in_executor(
            None, generate_script_with_ollama, concept
        )
        
        slide_paths, audio_paths = [], []
        
        # 2. Render slides + audio per slide
        for slide in script["slides"]:
            n = slide["slide_number"]
            img_path = tmp_dir / f"slide_{n}.png"
            aud_path = tmp_dir / f"audio_{n}.mp3"
            
            render_slide(slide, img_path)
            await asyncio.get_event_loop().run_in_executor(
                None, generate_narration, slide["narration"], aud_path
            )
            slide_paths.append(img_path)
            audio_paths.append(aud_path)
        
        # 3. Assemble video
        output_path = ARTIFACTS_DIR / f"{job_id}.mp4"
        await asyncio.get_event_loop().run_in_executor(
            None, assemble_video, slide_paths, audio_paths, output_path
        )
        
        job_store.update_status(
            job_id, JobStatus.COMPLETED,
            artifact_path=str(output_path),
            cost_estimate_usd=0.005  # Claude API cost estimate
        )
        logger.info(f"[{job_id}] Completed successfully.")
        
    except Exception as e:
        logger.error(f"[{job_id}] Pipeline failed: {e}", exc_info=True)
        job_store.update_status(job_id, JobStatus.FAILED, error_message=str(e))
    
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)