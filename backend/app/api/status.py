"""
Job status API endpoint with exam mode support and resume functionality.
"""
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query

from ..schemas.output_schema import JobStatus, ResumeResponse
from ..services.job_store import job_store
from ..services.checkpoint_service import CheckpointService
from ..services.llm_evaluator import resume_evaluation, load_config

router = APIRouter()


def run_async_resume(job_id: str, exam_mode: Optional[str] = None):
    """Wrapper to run async resume in a new event loop."""
    asyncio.run(resume_evaluation(job_id, exam_mode))


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the status of an evaluation job with detailed progress.
    
    Returns:
        - status: 'processing' | 'completed' | 'failed'
        - stage: Current pipeline stage
        - exam_mode: Detected/specified exam mode
        - completed_sections: List of evaluated sections
        - error: Error message if failed
    """
    job = job_store.get_job(job_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    # Get additional progress from checkpoint
    config = load_config()
    checkpoint = CheckpointService(job_id, config.get("paths", {}).get("checkpoints", "./checkpoints"))
    checkpoint_data = checkpoint.load()
    
    stage = None
    completed_sections = []
    exam_mode = None
    
    if checkpoint_data:
        stage = checkpoint_data.get("stage")
        completed_sections = checkpoint_data.get("completed_sections", [])
        # Try to get mode from final result or section results
        if "final_result" in checkpoint_data:
            exam_mode = checkpoint_data["final_result"].get("exam_mode")
        elif completed_sections:
            first_section = checkpoint_data.get("section_results", {}).get(completed_sections[0], {})
            exam_mode = first_section.get("mode")
    
    return JobStatus(
        job_id=job["job_id"],
        status=job["status"],
        stage=stage,
        exam_mode=exam_mode,
        completed_sections=completed_sections,
        error=job.get("error"),
        created_at=job.get("created_at"),
        updated_at=job.get("updated_at")
    )


@router.post("/resume/{job_id}", response_model=ResumeResponse)
async def resume_job(
    job_id: str, 
    background_tasks: BackgroundTasks,
    exam_mode: Optional[str] = Query(None, description="Override exam mode: PT-1 or PT-2")
):
    """
    Resume a failed or interrupted evaluation job from its checkpoint.
    
    The job will continue from where it left off:
    - If OCR was complete, skips OCR
    - If some sections were evaluated, resumes from next section
    
    Args:
        job_id: Job ID to resume
        exam_mode: Optional override for exam mode (PT-1 or PT-2)
    """
    job = job_store.get_job(job_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    if job["status"] == "completed":
        raise HTTPException(status_code=400, detail="Job already completed")
    
    if job["status"] == "processing":
        raise HTTPException(status_code=400, detail="Job is already processing")
    
    # Validate exam mode if provided
    if exam_mode and exam_mode not in ["PT-1", "PT-2"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid exam mode '{exam_mode}'. Must be 'PT-1' or 'PT-2'."
        )
    
    # Check if checkpoint exists
    config = load_config()
    checkpoint = CheckpointService(job_id, config.get("paths", {}).get("checkpoints", "./checkpoints"))
    checkpoint_data = checkpoint.load()
    
    if not checkpoint_data:
        raise HTTPException(
            status_code=404, 
            detail=f"No checkpoint found for job '{job_id}'. Cannot resume."
        )
    
    current_stage = checkpoint_data.get("stage", "UNKNOWN")
    
    # Update job status to processing
    job_store.update_job(job_id, "processing", error=None)
    
    # Start background resume task
    background_tasks.add_task(run_async_resume, job_id, exam_mode)
    
    return ResumeResponse(
        job_id=job_id,
        status="processing",
        message=f"Resuming evaluation from checkpoint" + (f" with mode {exam_mode}" if exam_mode else ""),
        resumed_from_stage=current_stage
    )


@router.get("/checkpoint/{job_id}")
async def get_checkpoint_details(job_id: str):
    """
    Get detailed checkpoint information for debugging/monitoring.
    """
    config = load_config()
    checkpoint = CheckpointService(job_id, config.get("paths", {}).get("checkpoints", "./checkpoints"))
    checkpoint_data = checkpoint.load()
    
    if not checkpoint_data:
        raise HTTPException(status_code=404, detail=f"No checkpoint for job '{job_id}'")
    
    # Get exam mode from results
    exam_mode = None
    if "section_results" in checkpoint_data:
        for section_data in checkpoint_data["section_results"].values():
            if "mode" in section_data:
                exam_mode = section_data["mode"]
                break
    
    # Return sanitized checkpoint (without full OCR text to keep response small)
    return {
        "job_id": job_id,
        "stage": checkpoint_data.get("stage"),
        "exam_mode": exam_mode,
        "completed_sections": checkpoint_data.get("completed_sections", []),
        "has_ocr_texts": bool(checkpoint_data.get("ocr_texts")),
        "has_structure": bool(checkpoint_data.get("structure")),
        "section_results_available": list(checkpoint_data.get("section_results", {}).keys()),
        "created_at": checkpoint_data.get("created_at"),
        "updated_at": checkpoint_data.get("updated_at")
    }
