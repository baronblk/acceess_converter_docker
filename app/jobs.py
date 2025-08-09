"""
Access Database Converter v2.0
Copyright © 2025 GCNG Software - Rene Süß

Lizenziert unter der Business Source License 1.1
Nicht-kommerzielle Nutzung gestattet.
Kommerzielle Nutzung nur mit schriftlicher Genehmigung.

Diese Software wird automatisch am 09. August 2030 unter MIT-Lizenz freigegeben.

Vollständige Lizenz: siehe LICENSE-Datei im Projektverzeichnis
Kontakt für kommerzielle Lizenz: baronblk@googlemail.com
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    file_path: str
    original_filename: str
    status: JobStatus = JobStatus.UPLOADED
    progress: int = 0
    message: str = "File uploaded"
    created_at: datetime = field(default_factory=datetime.now)
    tables: List[str] = field(default_factory=list)
    table_data: Dict[str, Any] = field(default_factory=dict)


class JobManager:
    """Thread-safe job manager for handling conversion jobs"""
    
    def __init__(self, max_workers: int = 3):
        self.jobs: Dict[str, Job] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()
        
    def create_job(self, job_id: str, file_path: str, original_filename: str) -> Job:
        """Create a new job"""
        with self._lock:
            job = Job(
                job_id=job_id,
                file_path=file_path,
                original_filename=original_filename
            )
            self.jobs[job_id] = job
            logger.info(f"Created job {job_id} for file {original_filename}")
            return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self._lock:
            return self.jobs.get(job_id)
    
    def update_job_status(self, job_id: str, status: JobStatus):
        """Update job status"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = status
                logger.info(f"Job {job_id} status updated to {status.value}")
    
    def update_job_progress(self, job_id: str, progress: int, message: str = ""):
        """Update job progress"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].progress = progress
                if message:
                    self.jobs[job_id].message = message
                logger.debug(f"Job {job_id} progress: {progress}% - {message}")
    
    def update_job_tables(self, job_id: str, tables: List[str]):
        """Update job with table list"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].tables = tables
                logger.info(f"Job {job_id} found {len(tables)} tables")
    
    def update_job_data(self, job_id: str, table_data: Dict[str, Any]):
        """Update job with table data"""
        with self._lock:
            if job_id in self.jobs:
                self.jobs[job_id].table_data = table_data
                logger.info(f"Job {job_id} data loaded for {len(table_data)} tables")
    
    def remove_job(self, job_id: str):
        """Remove job from manager"""
        with self._lock:
            if job_id in self.jobs:
                del self.jobs[job_id]
                logger.info(f"Job {job_id} removed")
    
    def get_all_jobs(self) -> Dict[str, Job]:
        """Get all jobs (for monitoring/admin)"""
        with self._lock:
            return self.jobs.copy()
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old jobs"""
        with self._lock:
            current_time = datetime.now()
            to_remove = []
            
            for job_id, job in self.jobs.items():
                age_hours = (current_time - job.created_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    to_remove.append(job_id)
            
            for job_id in to_remove:
                try:
                    # Clean up file if exists
                    import os
                    if os.path.exists(self.jobs[job_id].file_path):
                        os.remove(self.jobs[job_id].file_path)
                except Exception as e:
                    logger.error(f"Error cleaning up job {job_id}: {str(e)}")
                finally:
                    del self.jobs[job_id]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old jobs")
    
    def shutdown(self):
        """Shutdown the job manager"""
        logger.info("Shutting down job manager...")
        self.executor.shutdown(wait=True)
        logger.info("Job manager shutdown complete")
