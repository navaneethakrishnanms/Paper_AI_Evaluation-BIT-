"""
File upload API endpoint.
PT-II ONLY - No exam mode selection required.
"""
import uuid
import asyncio
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks

from ..schemas.output_schema import UploadResponse
from ..services.job_store import job_store
from ..services.llm_evaluator import run_evaluation_task, load_config

router = APIRouter()


def run_async_evaluation(
    job_id: str, 
    question_path: str, 
    answer_path: str, 
    student_path: str
):
    """
    Wrapper to run async evaluation in a new event loop (for background thread).
    """
    asyncio.run(run_evaluation_task(job_id, question_path, answer_path, student_path))


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    question_paper: UploadFile = File(..., description="Question paper PDF"),
    answer_key: UploadFile = File(..., description="Answer key PDF"),
    student_sheet: UploadFile = File(..., description="Student answer sheet PDF")
):
    """
    Upload three PDF files for evaluation.
    
    This endpoint accepts:
    - Question paper PDF
    - Answer key PDF
    - Student answer sheet PDF
    
    The system will:
    1. Extract text from all PDFs using OCR
    2. Build a question model identifying types (MCQ, descriptive, etc.)
    3. Semantically map student answers to questions
    4. Evaluate with type-aware rules (strict for MCQ, liberal for descriptive)
    5. Aggregate results applying best-2-of-3 rule per section
    
    Returns:
        job_id to track progress via /api/status/{job_id}
    """
    # Validate file types
    for file in [question_paper, answer_key, student_sheet]:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' is not a PDF. Only PDF files are accepted."
            )
    
    # Generate job ID from student paper filename
    # Extract filename without extension and add "-result" suffix
    student_filename = Path(student_sheet.filename).stem  # e.g., "7376242AD231" from "7376242AD231.pdf"
    base_job_id = f"{student_filename}-result"
    
    # Load config for paths
    config = load_config()
    uploads_dir = Path(config.get("paths", {}).get("uploads", "./uploads"))
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle duplicate filenames by adding (1), (2), etc.
    job_id = base_job_id
    job_dir = uploads_dir / job_id
    counter = 1
    while job_dir.exists():
        job_id = f"{base_job_id}({counter})"
        job_dir = uploads_dir / job_id
        counter += 1
    
    # Create job directory
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
    question_path = job_dir / "question_paper.pdf"
    answer_path = job_dir / "answer_key.pdf"
    student_path = job_dir / "student_sheet.pdf"
    
    try:
        with open(question_path, "wb") as f:
            content = await question_paper.read()
            f.write(content)
        
        with open(answer_path, "wb") as f:
            content = await answer_key.read()
            f.write(content)
        
        with open(student_path, "wb") as f:
            content = await student_sheet.read()
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save files: {str(e)}")
    
    # Create job entry
    job_store.create_job(job_id)
    
    # Start background evaluation task
    background_tasks.add_task(
        run_async_evaluation,
        job_id,
        str(question_path),
        str(answer_path),
        str(student_path)
    )
    
    return UploadResponse(
        job_id=job_id,
        status="processing",
        message=f"PT-II evaluation started. Use /api/status/{job_id} to check progress.",
        exam_mode="PT-II"
    )
