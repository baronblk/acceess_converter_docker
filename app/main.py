from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
import aiofiles
import os
import shutil
from typing import List, Optional
import uuid
from datetime import datetime
import zipfile
import asyncio

from .core.config import settings
from .core.logging import setup_logging
from .jobs import JobManager, JobStatus
from .services.ucan import AccessService
from .services.export import ExportService
from .models import ConversionRequest, JobResponse

# Setup logging
logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="Access Database Converter",
    description="Convert Access databases to CSV, XLSX, JSON, and PDF formats",
    version="2.0.0"
)

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Initialize services
job_manager = JobManager()
access_service = AccessService()
export_service = ExportService()

# Ensure upload and export directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with upload interface"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/diagnostics/ucanaccess")
async def ucanaccess_diagnostics():
    """UCanAccess diagnostics endpoint"""
    try:
        diagnosis = access_service.diagnose_ucanaccess()
        return {
            "timestamp": datetime.now().isoformat(),
            "diagnosis": diagnosis
        }
    except Exception as e:
        logger.error(f"Diagnostics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")


@app.post("/upload", response_model=JobResponse)
async def upload_database(file: UploadFile = File(...)):
    """Upload Access database file"""
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith(('.mdb', '.accdb')):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only .mdb and .accdb files are supported."
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}_{file.filename}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Create job
        filename = file.filename or "unknown.accdb"
        job_manager.create_job(job_id, file_path, filename)
        
        logger.info(f"File uploaded successfully: {filename} (Job ID: {job_id})")
        
        return JobResponse(
            job_id=job_id,
            filename=filename,
            status=JobStatus.UPLOADED.value,
            message="File uploaded successfully"
        )
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/tables/{job_id}")
async def get_tables(job_id: str):
    """Get list of tables from uploaded database"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.UPLOADED:
            raise HTTPException(status_code=400, detail="File not ready for table listing")
        
        # Extract tables using Access service
        tables = await run_in_threadpool(access_service.get_tables, job.file_path)
        
        # Update job status
        job_manager.update_job_tables(job_id, tables)
        
        return {
            "job_id": job_id,
            "tables": tables,
            "table_count": len(tables)
        }
        
    except Exception as e:
        logger.error(f"Error getting tables for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get tables: {str(e)}")


@app.get("/tables/{job_id}/page", response_class=HTMLResponse)
async def tables_page(request: Request, job_id: str):
    """Table selection page"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return templates.TemplateResponse("tables.html", {
            "request": request,
            "job": job,
            "job_id": job_id
        })
        
    except Exception as e:
        logger.error(f"Error loading tables page for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/convert/{job_id}")
async def start_conversion(
    job_id: str,
    request: ConversionRequest
):
    """Start conversion job"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.tables:
            raise HTTPException(status_code=400, detail="No tables available for conversion")
        
        # Start background conversion
        asyncio.create_task(
            _process_conversion(job_id, request.selected_tables, request.export_format)
        )
        
        # Update job status
        job_manager.update_job_status(job_id, JobStatus.PROCESSING)
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Conversion started"
        }
        
    except Exception as e:
        logger.error(f"Error starting conversion for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and progress"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job_id,
            "status": job.status.value,
            "progress": job.progress,
            "message": job.message,
            "created_at": job.created_at.isoformat(),
            "download_ready": job.status == JobStatus.COMPLETED
        }
        
    except Exception as e:
        logger.error(f"Error getting status for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{job_id}")
async def download_results(job_id: str):
    """Download conversion results as ZIP file"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Conversion not completed")
        
        # Create ZIP file with all exports
        zip_path = os.path.join(settings.EXPORT_DIR, f"{job_id}_export.zip")
        
        if not os.path.exists(zip_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return FileResponse(
            path=zip_path,
            filename=f"{job.original_filename}_export.zip",
            media_type="application/zip"
        )
        
    except Exception as e:
        logger.error(f"Error downloading results for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_conversion(job_id: str, selected_tables: List[str], export_format: str):
    """Background task for processing conversion"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return
        
        # Get data from Access database
        job_manager.update_job_progress(job_id, 10, "Reading database...")
        data = await run_in_threadpool(access_service.get_table_data, job.file_path, selected_tables)
        
        # Export data based on format
        job_manager.update_job_progress(job_id, 50, "Converting data...")
        export_files = await export_service.export_data(data, export_format, job_id)
        
        # Create ZIP file
        job_manager.update_job_progress(job_id, 80, "Creating archive...")
        zip_path = os.path.join(settings.EXPORT_DIR, f"{job_id}_export.zip")
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in export_files:
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname)
        
        # Clean up individual files
        for file_path in export_files:
            try:
                os.remove(file_path)
            except:
                pass
        
        # Update job as completed
        job_manager.update_job_status(job_id, JobStatus.COMPLETED)
        job_manager.update_job_progress(job_id, 100, "Conversion completed")
        
        logger.info(f"Conversion completed for job {job_id}")
        
    except Exception as e:
        logger.error(f"Conversion error for job {job_id}: {str(e)}")
        job_manager.update_job_status(job_id, JobStatus.FAILED)
        job_manager.update_job_progress(job_id, 0, f"Conversion failed: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("Access Database Converter started")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"Export directory: {settings.EXPORT_DIR}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Access Database Converter shutting down")
    # Clean up temp files
    try:
        for job_id, job in job_manager.jobs.items():
            if os.path.exists(job.file_path):
                os.remove(job.file_path)
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
