"""
Pydantic schemas for Anna University exam evaluation.
Uses exact output format from master specification.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============ Enums ============

class ExamMode(str, Enum):
    """Exam mode types."""
    PT1 = "PT-1"
    PT2 = "PT-2"


class EvaluationStatus(str, Enum):
    """Qualitative evaluation labels."""
    CORRECT = "Correct"
    PARTIALLY_CORRECT = "Partially Correct"
    INCORRECT = "Incorrect"
    NOT_ATTEMPTED = "Not Attempted"


# ============ Subdivision-Level Schemas ============

class SubdivisionResult(BaseModel):
    """Result for a single subdivision (i, ii, iii, iv)."""
    status: str = Field(..., description="Correct | Partially Correct | Incorrect | Not Attempted")
    marks_awarded: float = Field(0, ge=0, description="Marks awarded for this subdivision")


class QuestionResult(BaseModel):
    """Result for a single question with subdivisions (Anna University format)."""
    subdivisions: Dict[str, SubdivisionResult] = Field(default_factory=dict)
    question_total: float = Field(0, ge=0, description="Total marks awarded for this question")
    question_max: float = Field(0, ge=0, description="Maximum possible marks from answer key")
    feedback: str = Field("", description="Concise academic feedback")
    attempted: bool = Field(True, description="Whether student attempted this question")


# ============ Section-Level Schemas ============

class SectionEvaluationResult(BaseModel):
    """
    Evaluation result for a section (LLM output format).
    Matches the exact specification.
    """
    section: str = Field(..., description="Section letter (A, B, C)")
    exam_mode: str = Field(..., description="Exam mode (PT-1 or PT-2)")
    questions: Dict[str, QuestionResult] = Field(default_factory=dict)


# ============ Final Result Schemas ============

class SectionFinalResult(BaseModel):
    """Final result for a section after drop-lowest rule."""
    retained_questions: List[str] = Field(default_factory=list)
    discarded_question: Optional[str] = Field(None, description="Lowest scored question dropped")
    questions: Dict[str, QuestionResult] = Field(default_factory=dict)
    section_total: float = Field(0, ge=0, description="Section total (retained only)")
    section_max_allowed: float = Field(0, ge=0, description="Max allowed per mode")


class EvaluationResult(BaseModel):
    """Final aggregated result."""
    student_id: str = Field("UNKNOWN", description="Student identifier")
    exam_mode: str = Field("PT-2", description="Exam mode (PT-1 or PT-2)")
    sections: Dict[str, SectionFinalResult] = Field(default_factory=dict)
    section_totals: Dict[str, float] = Field(default_factory=dict)
    grand_total: float = Field(0, ge=0, description="Grand total across all sections")
    max_possible: int = Field(50, description="Maximum possible marks")
    percentage: float = Field(0, ge=0, le=100, description="Percentage score")
    grade: str = Field("", description="Letter grade")
    overall_feedback: str = Field("", description="Overall feedback")


# ============ API Response Schemas ============

class JobStatus(BaseModel):
    """Job status response."""
    job_id: str
    status: str = Field(..., description="processing | completed | failed")
    stage: Optional[str] = Field(None, description="Current pipeline stage")
    exam_mode: Optional[str] = Field(None, description="Detected exam mode")
    completed_sections: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UploadResponse(BaseModel):
    """Response after file upload."""
    job_id: str
    status: str = "processing"
    message: str = "Evaluation started"
    exam_mode: Optional[str] = Field(None, description="Detected or specified mode")


class ResumeResponse(BaseModel):
    """Response after resume request."""
    job_id: str
    status: str
    message: str
    resumed_from_stage: Optional[str] = None


class ResultResponse(BaseModel):
    """Response containing evaluation result."""
    job_id: str
    status: str
    exam_mode: str
    result: Optional[EvaluationResult] = None
    error: Optional[str] = None
