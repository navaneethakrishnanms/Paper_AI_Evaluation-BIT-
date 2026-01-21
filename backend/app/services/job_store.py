"""
In-memory job store for tracking evaluation jobs.
"""
import threading
from typing import Dict, Optional, Any
from datetime import datetime


class JobStore:
    """Thread-safe in-memory job store."""
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def create_job(self, job_id: str) -> Dict[str, Any]:
        """Create a new job entry."""
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "processing",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "error": None,
                "result": None
            }
            return self._jobs[job_id].copy()
    
    def update_job(self, job_id: str, status: str, error: Optional[str] = None, result: Optional[Dict] = None):
        """Update job status."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = status
                self._jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()
                if error:
                    self._jobs[job_id]["error"] = error
                if result:
                    self._jobs[job_id]["result"] = result
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        with self._lock:
            if job_id in self._jobs:
                return self._jobs[job_id].copy()
            return None
    
    def get_result(self, job_id: str) -> Optional[Dict]:
        """Get evaluation result for a job."""
        with self._lock:
            if job_id in self._jobs:
                return self._jobs[job_id].get("result")
            return None


# Global job store instance
job_store = JobStore()
