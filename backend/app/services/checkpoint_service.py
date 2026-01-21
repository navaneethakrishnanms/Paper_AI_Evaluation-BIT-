"""
Checkpoint service for saving and loading evaluation progress.
Enables resume from last successful stage after rate limits or failures.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class CheckpointService:
    """Manages checkpoint persistence for staged evaluation."""
    
    STAGES = [
        "OCR_COMPLETE",
        "EVALUATION_COMPLETE",
        "AGGREGATION_COMPLETE"
    ]
    
    def __init__(self, job_id: str, checkpoint_dir: str = "./checkpoints"):
        self.job_id = job_id
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_file = self.checkpoint_dir / f"{job_id}_checkpoint.json"
    
    def load(self) -> Optional[Dict[str, Any]]:
        """Load existing checkpoint if it exists."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        return None
    
    def save(self, data: Dict[str, Any]):
        """Save checkpoint to disk."""
        data["updated_at"] = datetime.utcnow().isoformat()
        with open(self.checkpoint_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def init_checkpoint(self) -> Dict[str, Any]:
        """Initialize a new checkpoint."""
        checkpoint = {
            "job_id": self.job_id,
            "stage": "STARTED",
            "completed_sections": [],
            "ocr_texts": {},
            "structure": {},
            "section_results": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        self.save(checkpoint)
        return checkpoint
    
    def get_or_create(self) -> Dict[str, Any]:
        """Get existing checkpoint or create new one."""
        checkpoint = self.load()
        if checkpoint is None:
            checkpoint = self.init_checkpoint()
        return checkpoint
    
    def save_ocr_complete(self, question_text: str, answer_key_text: str, student_text: str):
        """Save OCR results."""
        checkpoint = self.get_or_create()
        checkpoint["stage"] = "OCR_COMPLETE"
        checkpoint["ocr_texts"] = {
            "question_paper": question_text,
            "answer_key": answer_key_text,
            "student_answers": student_text
        }
        self.save(checkpoint)
    
    def save_structure(self, structure: Dict[str, Any]):
        """Save extracted structure."""
        checkpoint = self.get_or_create()
        checkpoint["stage"] = "STRUCTURE_EXTRACTED"
        checkpoint["structure"] = structure
        self.save(checkpoint)
    
    def save_section_result(self, section: str, result: Dict[str, Any]):
        """Save evaluation result for a section."""
        checkpoint = self.get_or_create()
        checkpoint["section_results"][section] = result
        checkpoint["completed_sections"].append(section)
        checkpoint["stage"] = f"SECTION_{section}_EVALUATED"
        self.save(checkpoint)
    
    def save_final_result(self, final_result: Dict[str, Any]):
        """Save final aggregated result."""
        checkpoint = self.get_or_create()
        checkpoint["stage"] = "AGGREGATION_COMPLETE"
        checkpoint["final_result"] = final_result
        self.save(checkpoint)
    
    def is_ocr_complete(self) -> bool:
        """Check if OCR stage is complete."""
        checkpoint = self.load()
        if checkpoint is None:
            return False
        stage_idx = self.STAGES.index("OCR_COMPLETE") if "OCR_COMPLETE" in self.STAGES else -1
        current_idx = self.STAGES.index(checkpoint.get("stage", "")) if checkpoint.get("stage") in self.STAGES else -1
        return current_idx >= stage_idx
    
    def is_section_complete(self, section: str) -> bool:
        """Check if a section has been evaluated."""
        checkpoint = self.load()
        if checkpoint is None:
            return False
        return section in checkpoint.get("completed_sections", [])
    
    def get_pending_sections(self) -> List[str]:
        """Get list of sections not yet evaluated."""
        checkpoint = self.load()
        completed = checkpoint.get("completed_sections", []) if checkpoint else []
        return [s for s in ["A", "B", "C"] if s not in completed]
    
    def get_ocr_texts(self) -> Optional[Dict[str, str]]:
        """Get saved OCR texts."""
        checkpoint = self.load()
        if checkpoint and "ocr_texts" in checkpoint:
            return checkpoint["ocr_texts"]
        return None
    
    def get_structure(self) -> Optional[Dict[str, Any]]:
        """Get saved structure."""
        checkpoint = self.load()
        if checkpoint and "structure" in checkpoint:
            return checkpoint["structure"]
        return None
    
    def get_section_results(self) -> Dict[str, Any]:
        """Get all completed section results."""
        checkpoint = self.load()
        if checkpoint:
            return checkpoint.get("section_results", {})
        return {}
    
    def cleanup(self):
        """Remove checkpoint file after successful completion."""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
