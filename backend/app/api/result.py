"""
Result retrieval API endpoint.
"""
from fastapi import APIRouter, HTTPException

from ..services.job_store import job_store

router = APIRouter()


@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """
    Get the evaluation result for a completed job.
    
    Returns the full evaluation JSON if the job is completed.
    """
    job = job_store.get_job(job_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    
    if job["status"] == "processing":
        raise HTTPException(
            status_code=202,
            detail="Job is still processing. Please check back later."
        )
    
    if job["status"] == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Job failed: {job.get('error', 'Unknown error')}"
        )
    
    result = job_store.get_result(job_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found")
    
    return result
