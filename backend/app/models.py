"""
Pydantic models for API requests and responses
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExportFormat(str, Enum):
    """Supported export formats"""
    CSV = "csv"
    XLSX = "xlsx" 
    JSON = "json"
    PDF = "pdf"


class JobStatus(str, Enum):
    """Job processing status"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TableInfo(BaseModel):
    """Information about a database table"""
    name: str
    row_count: int
    column_count: int
    columns: List[str]


class UploadResponse(BaseModel):
    """Response for file upload"""
    file_id: str
    filename: str
    size: int
    uploaded_at: datetime


class TablesResponse(BaseModel):
    """Response for table listing"""
    file_id: str
    tables: List[TableInfo]
    total_tables: int


class JobRequest(BaseModel):
    """Request to start a new job"""
    file_id: str
    format: ExportFormat
    selected_tables: List[str] = Field(..., min_items=1)
    options: Optional[Dict[str, Any]] = {}


class JobProgress(BaseModel):
    """Job progress information"""
    current_table: Optional[str] = None
    completed_tables: int = 0
    total_tables: int = 0
    percentage: float = Field(ge=0, le=100)
    message: str = ""


class ResultFile(BaseModel):
    """Information about an exported file"""
    table_name: str
    filename: str
    format: ExportFormat
    size: int
    download_url: str


class JobResponse(BaseModel):
    """Detailed job information"""
    job_id: str
    file_id: str
    filename: str
    format: ExportFormat
    selected_tables: List[str]
    status: JobStatus
    progress: JobProgress
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_files: List[ResultFile] = []
    zip_download_url: Optional[str] = None
    error: Optional[str] = None
    options: Dict[str, Any] = {}


class JobSummary(BaseModel):
    """Summary information for job listing"""
    job_id: str
    filename: str
    format: ExportFormat
    status: JobStatus
    progress_percentage: float
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    table_count: int


class JobListResponse(BaseModel):
    """Response for job listing"""
    jobs: List[JobSummary]
    total: int


class LogEntry(BaseModel):
    """Single log entry"""
    timestamp: datetime
    level: str
    message: str
    job_id: Optional[str] = None
    request_id: Optional[str] = None


class LogResponse(BaseModel):
    """Response for log viewing"""
    job_id: str
    logs: List[LogEntry]
    total_lines: int


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    job_id: Optional[str] = None
    request_id: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]  # service_name -> status


class ProgressUpdate(BaseModel):
    """WebSocket progress update"""
    job_id: str
    status: JobStatus
    progress: JobProgress
    timestamp: datetime
    message: Optional[str] = None


# Internal models for job data storage
class JobData(BaseModel):
    """Internal job data structure"""
    job_id: str
    file_id: str
    file_path: str
    filename: str
    format: ExportFormat
    selected_tables: List[str]
    status: JobStatus = JobStatus.QUEUED
    progress: JobProgress = JobProgress(percentage=0, completed_tables=0, total_tables=0)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result_files: List[ResultFile] = []
    error: Optional[str] = None
    options: Dict[str, Any] = {}
    
    class Config:
        use_enum_values = True


class FileUpload(BaseModel):
    """File upload information"""
    file_id: str
    filename: str
    original_filename: str
    file_path: str
    size: int
    uploaded_at: datetime
    mime_type: str
    
    class Config:
        use_enum_values = True
