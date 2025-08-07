"""
API routes for the Access Database Converter
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, WebSocket
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Optional
import os
import asyncio
from pathlib import Path
import tempfile
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger, logger_setup
from app.models import (
    UploadResponse, TablesResponse, JobRequest, JobResponse, 
    JobListResponse, LogResponse, ExportFormat
)
from app.services.ucanaccess import ucanaccess_service, UCanAccessError
from app.services.jobs import job_service
from app.utils import file_manager, validate_access_file

logger = get_logger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """Upload an Access database file"""
    request_id = logger_setup.generate_request_id()
    logger_setup.set_request_context(request_id=request_id)
    
    logger.info("File upload started", filename=file.filename, request_id=request_id)
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_ext} not allowed. Allowed types: {settings.allowed_extensions}"
        )
    
    # Read file content
    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_upload_mb}MB"
            )
        
        # Save file
        file_id, file_path = file_manager.save_uploaded_file(content, file.filename)
        
        # Validate Access file
        is_valid, error_msg = validate_access_file(file_path)
        if not is_valid:
            # Clean up invalid file
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Test connection to database
        try:
            with ucanaccess_service:
                success, message = ucanaccess_service.test_connection(str(file_path))
                if not success:
                    raise HTTPException(status_code=400, detail=f"Cannot read Access database: {message}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Database connection failed: {str(e)}")
        
        logger.info("File uploaded successfully", 
                   file_id=file_id,
                   filename=file.filename,
                   size_mb=len(content) / (1024 * 1024))
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            size=len(content),
            uploaded_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed", filename=file.filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/tables", response_model=TablesResponse)
async def list_tables(file_id: str = Query(...)):
    """List all tables in the uploaded Access database"""
    logger.info("Listing tables", file_id=file_id)
    
    # Get file path
    file_path = file_manager.get_file_path(file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        # Connect to database and get tables
        with ucanaccess_service:
            ucanaccess_service.connect(str(file_path))
            tables = ucanaccess_service.list_tables()
        
        logger.info("Tables listed successfully", 
                   file_id=file_id,
                   table_count=len(tables))
        
        return TablesResponse(
            file_id=file_id,
            tables=tables,
            total_tables=len(tables)
        )
        
    except UCanAccessError as e:
        logger.error("Failed to list tables", file_id=file_id, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error listing tables", file_id=file_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list tables")


@router.post("/jobs", response_model=JobResponse)
async def create_job(job_request: JobRequest):
    """Start a new conversion job"""
    logger.info("Creating conversion job", 
                file_id=job_request.file_id, 
                format=job_request.format,
                table_count=len(job_request.selected_tables))
    
    # Validate file exists
    file_path = file_manager.get_file_path(job_request.file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Validate selected tables exist
    try:
        with ucanaccess_service:
            ucanaccess_service.connect(str(file_path))
            available_tables = ucanaccess_service.list_tables()
            available_table_names = {table.name for table in available_tables}
            
            invalid_tables = set(job_request.selected_tables) - available_table_names
            if invalid_tables:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid tables: {list(invalid_tables)}"
                )
    except UCanAccessError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to validate tables")
    
    try:
        # Create and enqueue job
        job_id = job_service.create_job(
            file_id=job_request.file_id,
            file_path=str(file_path),
            filename=file_path.name,
            format=job_request.format,
            selected_tables=job_request.selected_tables,
            options=job_request.options or {}
        )
        
        # Get job details to return
        job_response = job_service.get_job(job_id)
        if not job_response:
            raise HTTPException(status_code=500, detail="Failed to create job")
        
        logger.info("Job created successfully", 
                   job_id=job_id,
                   file_id=job_request.file_id)
        
        return job_response
        
    except Exception as e:
        logger.error("Failed to create job", 
                    file_id=job_request.file_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create job")


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job status and details"""
    logger.info("Getting job details", job_id=job_id)
    
    job_response = job_service.get_job(job_id)
    if not job_response:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_response


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(limit: int = Query(10, ge=1, le=100)):
    """List recent jobs"""
    logger.info("Listing jobs", limit=limit)
    
    jobs = job_service.list_jobs(limit)
    
    return JobListResponse(jobs=jobs, total=len(jobs))


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    logger.info("Cancelling job", job_id=job_id)
    
    success = job_service.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    
    return {"message": "Job cancelled successfully"}


@router.get("/jobs/{job_id}/download")
async def download_job_results(job_id: str):
    """Download ZIP file with all job results"""
    logger.info("Downloading job results", job_id=job_id)
    
    job_response = job_service.get_job(job_id)
    if not job_response:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_response.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    # Find ZIP file in export directory
    export_dir = Path(settings.export_path) / job_id
    zip_files = list(export_dir.glob("*.zip"))
    
    if not zip_files:
        raise HTTPException(status_code=404, detail="Export file not found")
    
    zip_file = zip_files[0]
    
    return FileResponse(
        path=str(zip_file),
        filename=f"{job_response.filename}_{job_response.format.value}_export.zip",
        media_type="application/zip"
    )


@router.get("/jobs/{job_id}/download/{table_name}")
async def download_table_result(job_id: str, table_name: str):
    """Download result file for a specific table"""
    logger.info("Downloading table result", job_id=job_id, table_name=table_name)
    
    job_response = job_service.get_job(job_id)
    if not job_response:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_response.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")
    
    # Find result file for the table
    result_file = None
    for rf in job_response.result_files:
        if rf.table_name == table_name:
            result_file = rf
            break
    
    if not result_file:
        raise HTTPException(status_code=404, detail="Table result not found")
    
    # Build file path
    export_dir = Path(settings.export_path) / job_id
    file_path = export_dir / result_file.filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_types = {
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".json": "application/json",
        ".pdf": "application/pdf"
    }
    
    file_ext = file_path.suffix.lower()
    media_type = media_types.get(file_ext, "application/octet-stream")
    
    return FileResponse(
        path=str(file_path),
        filename=result_file.filename,
        media_type=media_type
    )


@router.get("/logs/{job_id}", response_model=LogResponse)
async def get_job_logs(
    job_id: str, 
    lines: int = Query(100, ge=10, le=1000)
):
    """Get logs for a specific job"""
    logger.info("Getting job logs", job_id=job_id, lines=lines)
    
    # TODO: Implement log reading from log files
    # For now, return empty logs
    
    return LogResponse(
        job_id=job_id,
        logs=[],
        total_lines=0
    )


# WebSocket endpoint for real-time progress updates
@router.websocket("/jobs/{job_id}/ws")
async def websocket_job_progress(websocket, job_id: str):
    """WebSocket endpoint for real-time job progress"""
    await websocket.accept()
    
    try:
        # TODO: Listen for job progress updates
        # TODO: Send progress updates to client
        pass
    except Exception as e:
        logger.error("WebSocket error", job_id=job_id, error=str(e))
    finally:
        await websocket.close()
