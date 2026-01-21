"""
Exam Checkpoint Service - Caches Question Paper and Answer Key OCR results.

This provides EXAM-LEVEL caching so that QP and AK are only OCR-processed ONCE,
then reused for ALL student evaluations in the same exam batch.

Key Features:
- Generates exam_id from hash of QP+AK file contents
- Stores QP and AK OCR text permanently
- Used by llm_evaluator to skip redundant OCR
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file's contents."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks for large files
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()[:16]  # First 16 chars for shorter ID


def generate_exam_id(question_pdf_path: str, answer_key_pdf_path: str) -> str:
    """
    Generate a unique exam_id from QP and AK file hashes.
    Same QP + AK always produces the same exam_id.
    """
    qp_hash = compute_file_hash(question_pdf_path)
    ak_hash = compute_file_hash(answer_key_pdf_path)
    combined = f"{qp_hash}_{ak_hash}"
    return f"exam_{combined}"


class ExamCheckpointService:
    """
    Manages exam-level checkpoint for QP and AK OCR caching.
    
    Separate from per-student job checkpoints.
    One exam checkpoint can be reused by multiple student jobs.
    """
    
    def __init__(self, exam_id: str, checkpoint_dir: str = "./checkpoints"):
        self.exam_id = exam_id
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / f"{exam_id}_exam.json"
    
    def exists(self) -> bool:
        """Check if exam checkpoint exists."""
        return self.checkpoint_file.exists()
    
    def has_complete_ocr(self) -> bool:
        """Check if QP and AK OCR are both complete."""
        if not self.exists():
            return False
        
        data = self.load()
        return (
            data is not None and
            data.get("question_paper_text") and
            data.get("answer_key_text")
        )
    
    def load(self) -> Optional[Dict]:
        """Load existing exam checkpoint."""
        if self.exists():
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def save(self, data: Dict):
        """Save exam checkpoint to disk."""
        data["exam_id"] = self.exam_id
        data["updated_at"] = datetime.utcnow().isoformat()
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def save_ocr_results(self, question_text: str, answer_key_text: str):
        """
        Save QP and AK OCR results.
        This is called ONCE after first successful extraction.
        """
        data = self.load() or {}
        data["question_paper_text"] = question_text
        data["answer_key_text"] = answer_key_text
        data["ocr_completed_at"] = datetime.utcnow().isoformat()
        self.save(data)
    
    def get_question_paper_text(self) -> Optional[str]:
        """Get cached QP OCR text."""
        data = self.load()
        return data.get("question_paper_text") if data else None
    
    def get_answer_key_text(self) -> Optional[str]:
        """Get cached AK OCR text."""
        data = self.load()
        return data.get("answer_key_text") if data else None
    
    def get_ocr_texts(self) -> Optional[Dict[str, str]]:
        """Get both QP and AK OCR texts if available."""
        data = self.load()
        if data and data.get("question_paper_text") and data.get("answer_key_text"):
            return {
                "question_paper": data["question_paper_text"],
                "answer_key": data["answer_key_text"]
            }
        return None
