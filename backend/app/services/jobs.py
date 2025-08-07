"""
Job management service using Redis Queue (RQ)
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import redis
from rq import Queue, Job, Worker
from rq.job import JobStatus as RQJobStatus

from app.core.config import settings
from app.core.logging import get_logger, logger_setup
from app.models import (
    JobData, JobStatus, JobProgress, ExportFormat, 
    ResultFile, JobResponse, JobSummary
)
from app.utils import generate_job_id, create_export_directory

logger = get_logger(__name__)


class JobService:
    """Service for managing conversion jobs using Redis Queue"""
    
    def __init__(self):
        self.redis_conn = redis.from_url(settings.redis_url)
        self.queue = Queue(connection=self.redis_conn, default_timeout=settings.job_timeout)
        self._job_cache = {}  # In-memory cache for job data
    
    def create_job(
        self, 
        file_id: str, 
        file_path: str, 
        filename: str,
        format: ExportFormat, 
        selected_tables: List[str],
        options: Dict[str, Any] = None
    ) -> str:
        """Create a new conversion job"""
        job_id = generate_job_id()
        
        # Create job data
        job_data = JobData(
            job_id=job_id,
            file_id=file_id,
            file_path=file_path,
            filename=filename,
            format=format,
            selected_tables=selected_tables,
            status=JobStatus.QUEUED,
            progress=JobProgress(
                percentage=0,
                completed_tables=0,
                total_tables=len(selected_tables),
                message="Job queued"
            ),
            options=options or {}
        )
        
        # Save job data to Redis
        self._save_job_data(job_data)
        
        # Enqueue the job
        rq_job = self.queue.enqueue(
            'app.services.export.process_conversion_job',
            job_id,
            job_timeout=settings.job_timeout,
            job_id=job_id  # This sets the RQ job ID to match our job ID
        )
        
        logger.info("Job created and queued", 
                   job_id=job_id,
                   file_id=file_id,
                   format=format.value,
                   table_count=len(selected_tables))
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[JobResponse]:
        """Get job details and current status"""
        try:
            # Get job data from cache or Redis
            job_data = self._get_job_data(job_id)
            if not job_data:
                return None
            
            # Get RQ job status
            try:
                rq_job = Job.fetch(job_id, connection=self.redis_conn)
                self._update_job_status_from_rq(job_data, rq_job)
            except Exception as e:
                logger.warning("Could not fetch RQ job status", 
                             job_id=job_id, 
                             error=str(e))
            
            # Build response
            return self._build_job_response(job_data)
            
        except Exception as e:
            logger.error("Failed to get job", job_id=job_id, error=str(e))
            return None
    
    def list_jobs(self, limit: int = 10) -> List[JobSummary]:
        """List recent jobs"""
        try:
            # Get job IDs from Redis
            job_keys = self.redis_conn.keys("job:*")
            job_ids = [key.decode().split(":", 1)[1] for key in job_keys]
            
            # Sort by creation time (newest first)
            job_summaries = []
            for job_id in job_ids[-limit:]:
                job_data = self._get_job_data(job_id)
                if job_data:
                    summary = JobSummary(
                        job_id=job_id,
                        filename=job_data.filename,
                        format=job_data.format,
                        status=job_data.status,
                        progress_percentage=job_data.progress.percentage,
                        started_at=job_data.started_at,
                        finished_at=job_data.finished_at,
                        table_count=len(job_data.selected_tables)
                    )
                    job_summaries.append(summary)
            
            # Sort by start time (newest first)
            job_summaries.sort(
                key=lambda x: x.started_at or datetime.min, 
                reverse=True
            )
            
            return job_summaries
            
        except Exception as e:
            logger.error("Failed to list jobs", error=str(e))
            return []
    
    def update_job_progress(
        self, 
        job_id: str, 
        progress: JobProgress, 
        status: JobStatus = None
    ) -> bool:
        """Update job progress"""
        try:
            job_data = self._get_job_data(job_id)
            if not job_data:
                logger.warning("Job not found for progress update", job_id=job_id)
                return False
            
            # Update progress
            job_data.progress = progress
            
            if status:
                job_data.status = status
                
                # Set timestamps
                if status == JobStatus.RUNNING and not job_data.started_at:
                    job_data.started_at = datetime.utcnow()
                elif status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    job_data.finished_at = datetime.utcnow()
            
            # Save updated data
            self._save_job_data(job_data)
            
            logger.debug("Job progress updated", 
                        job_id=job_id,
                        status=job_data.status.value,
                        percentage=progress.percentage)
            
            return True
            
        except Exception as e:
            logger.error("Failed to update job progress", 
                        job_id=job_id, 
                        error=str(e))
            return False
    
    def add_result_file(self, job_id: str, result_file: ResultFile) -> bool:
        """Add a result file to the job"""
        try:
            job_data = self._get_job_data(job_id)
            if not job_data:
                return False
            
            job_data.result_files.append(result_file)
            self._save_job_data(job_data)
            
            logger.info("Result file added to job", 
                       job_id=job_id,
                       table_name=result_file.table_name,
                       filename=result_file.filename)
            
            return True
            
        except Exception as e:
            logger.error("Failed to add result file", 
                        job_id=job_id, 
                        error=str(e))
            return False
    
    def mark_job_failed(self, job_id: str, error_message: str) -> bool:
        """Mark job as failed with error message"""
        try:
            job_data = self._get_job_data(job_id)
            if not job_data:
                return False
            
            job_data.status = JobStatus.FAILED
            job_data.error = error_message
            job_data.finished_at = datetime.utcnow()
            
            self._save_job_data(job_data)
            
            logger.error("Job marked as failed", 
                        job_id=job_id,
                        error=error_message)
            
            return True
            
        except Exception as e:
            logger.error("Failed to mark job as failed", 
                        job_id=job_id, 
                        error=str(e))
            return False
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        try:
            # Cancel RQ job
            try:
                rq_job = Job.fetch(job_id, connection=self.redis_conn)
                rq_job.cancel()
            except Exception as e:
                logger.warning("Could not cancel RQ job", 
                             job_id=job_id, 
                             error=str(e))
            
            # Update job status
            job_data = self._get_job_data(job_id)
            if job_data:
                job_data.status = JobStatus.CANCELLED
                job_data.finished_at = datetime.utcnow()
                self._save_job_data(job_data)
            
            logger.info("Job cancelled", job_id=job_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cancel job", job_id=job_id, error=str(e))
            return False
    
    def get_queue_info(self) -> Dict[str, Any]:
        """Get information about the job queue"""
        try:
            return {
                "queued_jobs": len(self.queue),
                "failed_jobs": len(self.queue.failed_job_registry),
                "started_jobs": len(self.queue.started_job_registry),
                "finished_jobs": len(self.queue.finished_job_registry),
                "workers": len(Worker.all(connection=self.redis_conn))
            }
        except Exception as e:
            logger.error("Failed to get queue info", error=str(e))
            return {}
    
    def _save_job_data(self, job_data: JobData) -> None:
        """Save job data to Redis"""
        key = f"job:{job_data.job_id}"
        value = job_data.json()
        
        # Save to Redis with expiration (keep for 7 days)
        self.redis_conn.setex(key, 7 * 24 * 60 * 60, value)
        
        # Update cache
        self._job_cache[job_data.job_id] = job_data
    
    def _get_job_data(self, job_id: str) -> Optional[JobData]:
        """Get job data from cache or Redis"""
        # Check cache first
        if job_id in self._job_cache:
            return self._job_cache[job_id]
        
        # Get from Redis
        try:
            key = f"job:{job_id}"
            data = self.redis_conn.get(key)
            
            if data:
                job_data = JobData.parse_raw(data)
                self._job_cache[job_id] = job_data
                return job_data
            
        except Exception as e:
            logger.error("Failed to get job data from Redis", 
                        job_id=job_id, 
                        error=str(e))
        
        return None
    
    def _update_job_status_from_rq(self, job_data: JobData, rq_job: Job) -> None:
        """Update job status based on RQ job status"""
        rq_status_map = {
            RQJobStatus.QUEUED: JobStatus.QUEUED,
            RQJobStatus.STARTED: JobStatus.RUNNING,
            RQJobStatus.FINISHED: JobStatus.COMPLETED,
            RQJobStatus.FAILED: JobStatus.FAILED,
            RQJobStatus.CANCELED: JobStatus.CANCELLED
        }
        
        if rq_job.get_status() in rq_status_map:
            new_status = rq_status_map[rq_job.get_status()]
            
            if job_data.status != new_status:
                job_data.status = new_status
                
                # Update timestamps
                if new_status == JobStatus.RUNNING and not job_data.started_at:
                    job_data.started_at = datetime.utcnow()
                elif new_status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if not job_data.finished_at:
                        job_data.finished_at = datetime.utcnow()
                
                self._save_job_data(job_data)
    
    def _build_job_response(self, job_data: JobData) -> JobResponse:
        """Build JobResponse from JobData"""
        # Create ZIP download URL if job is completed and has result files
        zip_download_url = None
        if job_data.status == JobStatus.COMPLETED and job_data.result_files:
            zip_download_url = f"/api/jobs/{job_data.job_id}/download"
        
        return JobResponse(
            job_id=job_data.job_id,
            file_id=job_data.file_id,
            filename=job_data.filename,
            format=job_data.format,
            selected_tables=job_data.selected_tables,
            status=job_data.status,
            progress=job_data.progress,
            started_at=job_data.started_at,
            finished_at=job_data.finished_at,
            result_files=job_data.result_files,
            zip_download_url=zip_download_url,
            error=job_data.error,
            options=job_data.options
        )


# Global job service instance
job_service = JobService()
