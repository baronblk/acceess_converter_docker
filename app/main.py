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

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.concurrency import run_in_threadpool
import aiofiles
import os
import shutil
from typing import List, Optional
from pathlib import Path
import uuid
from datetime import datetime
import zipfile
import asyncio
import time
import threading

from .core.config import settings
from .core.logging import setup_logging, RequestLoggerAdapter, get_logger
from .jobs import JobManager, JobStatus
from .services.ucan import AccessService, list_tables_detailed
from .services.export import ExportService
from .models import ConversionRequest, JobResponse
from .utils import cleanup_uploads_for_file_id, cleanup_old_uploads, cleanup_old_logs

def normalize_file_path(old_path: str) -> str:
    """Normalize file paths for backward compatibility with old upload structure"""
    if old_path.startswith('/app/uploads/'):
        # Convert old path to new structure
        filename = os.path.basename(old_path)
        return os.path.join(settings.UPLOAD_DIR, filename)
    return old_path

# Setup logging
logger = setup_logging()

# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests"""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Create request logger
        request_logger = RequestLoggerAdapter(get_logger("request"), request_id)
        
        # Add request_id to request state for use in endpoints
        request.state.request_id = request_id
        request.state.logger = request_logger
        
        # Log request start
        start_time = time.time()
        request_logger.info(f"{request.method} {request.url.path}")
        
        # Process request
        try:
            response = await call_next(request)
            duration = int((time.time() - start_time) * 1000)
            
            # Log successful response
            request_logger.info(
                f"{request.method} {request.url.path} -> {response.status_code}",
                extra={'duration': duration}
            )
            
            return response
            
        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            
            # Log error response
            request_logger.error(
                f"{request.method} {request.url.path} -> ERROR: {str(e)}",
                extra={'duration': duration}
            )
            raise

# Initialize FastAPI app
app = FastAPI(
    title="Access Database Converter",
    description="Convert Access databases to CSV, XLSX, JSON, and PDF formats",
    version="2.0.0"
)

# Add middleware
app.add_middleware(RequestLoggingMiddleware)

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Initialize services
job_manager = JobManager()
access_service = AccessService()
export_service = ExportService()

# Ensure upload and export directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EXPORT_DIR, exist_ok=True)
os.makedirs(settings.LOGS_DIR, exist_ok=True)


# ============================================================================
# PERIODIC CLEANUP FUNCTIONALITY
# ============================================================================

cleanup_thread = None
cleanup_stop_event = threading.Event()

def periodic_cleanup_worker():
    """Hintergrund-Worker für periodische Bereinigung"""
    try:
        interval_minutes = settings.CLEANUP_INTERVAL_MINUTES
        logger.info(f"Periodische Bereinigung gestartet (Intervall: {interval_minutes} Minuten)")
        
        while not cleanup_stop_event.is_set():
            try:
                # Cleanup alte Uploads
                removed_uploads = cleanup_old_uploads(settings.CLEANUP_AFTER_HOURS)
                
                # Cleanup alte Logs  
                removed_logs = cleanup_old_logs(settings.CLEANUP_AFTER_HOURS)
                
                if removed_uploads or removed_logs:
                    logger.info(f"Periodische Bereinigung abgeschlossen: "
                              f"{len(removed_uploads)} Uploads, {len(removed_logs)} Logs entfernt")
                
            except Exception as e:
                logger.error(f"Fehler bei periodischer Bereinigung: {e}", exc_info=True)
            
            # Warten bis zum nächsten Cleanup oder Stop-Signal
            cleanup_stop_event.wait(timeout=interval_minutes * 60)
        
        logger.info("Periodische Bereinigung beendet")
        
    except Exception as e:
        logger.critical(f"Kritischer Fehler im Cleanup-Thread - Thread wird beendet: {e}", exc_info=True)

def start_periodic_cleanup():
    """Startet den periodischen Cleanup-Thread"""
    global cleanup_thread
    
    # Startup-Check: Validiere Cleanup-Konfiguration
    try:
        interval = settings.CLEANUP_INTERVAL_MINUTES
        if not isinstance(interval, int) or interval < 1:
            logger.error(f"Ungültige CLEANUP_INTERVAL_MINUTES: {interval} (muss >= 1 sein)")
            return
        logger.info(f"Cleanup-Konfiguration validiert: CLEANUP_INTERVAL_MINUTES={interval}, "
                   f"CLEANUP_AFTER_HOURS={settings.CLEANUP_AFTER_HOURS}")
    except AttributeError as e:
        logger.error(f"Cleanup-Konfiguration fehlt: {e}")
        return
    
    if cleanup_thread is None or not cleanup_thread.is_alive():
        cleanup_stop_event.clear()
        cleanup_thread = threading.Thread(target=periodic_cleanup_worker, daemon=True, name="PeriodicCleanupWorker")
        cleanup_thread.start()
        logger.info("Periodic cleanup thread gestartet")

def stop_periodic_cleanup():
    """Stoppt den periodischen Cleanup-Thread"""
    global cleanup_thread
    if cleanup_thread and cleanup_thread.is_alive():
        cleanup_stop_event.set()
        cleanup_thread.join(timeout=5)
        logger.info("Periodic cleanup thread gestoppt")

# Starte periodische Bereinigung beim App-Start
start_periodic_cleanup()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with upload interface"""
    # Berechne die maximale Upload-Größe in MB für das Frontend
    max_upload_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "max_upload_mb": max_upload_mb,
        "app_version": settings.APP_VERSION
    })


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/api/config")
async def get_config():
    """API endpoint für Frontend-Konfiguration"""
    return {
        "max_upload_mb": settings.MAX_UPLOAD_SIZE // (1024 * 1024),
        "max_upload_size": settings.MAX_UPLOAD_SIZE,
        "max_concurrent_jobs": settings.MAX_CONCURRENT_JOBS,
        "max_tables_per_db": settings.MAX_TABLES_PER_DB,
        "app_version": settings.APP_VERSION,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS
    }


@app.get("/diagnostics/cleanup")
async def cleanup_diagnostics(dry_run: bool = True):
    """
    Manuelle Bereinigung mit Diagnose-Funktionalität
    
    Args:
        dry_run: Wenn True, werden Dateien nur aufgelistet aber nicht gelöscht
    
    Returns:
        JSON mit Listen der (zu) entfernenden Dateien
    """
    try:
        result = {
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "settings": {
                "cleanup_after_hours": settings.CLEANUP_AFTER_HOURS,
                "upload_dir": settings.UPLOAD_DIR,
                "logs_dir": settings.LOGS_DIR
            },
            "uploads_removed": [],
            "logs_removed": []
        }
        
        if dry_run:
            # Simuliere Cleanup ohne Löschen
            from .utils import iter_files, age_hours
            
            # Prüfe Upload-Dateien
            upload_path = Path(settings.UPLOAD_DIR)
            if upload_path.exists():
                for file_path in iter_files(upload_path):
                    if age_hours(file_path) > settings.CLEANUP_AFTER_HOURS:
                        result["uploads_removed"].append({
                            "path": str(file_path),
                            "age_hours": round(age_hours(file_path), 1),
                            "size_bytes": file_path.stat().st_size if file_path.exists() else 0
                        })
            
            # Prüfe Log-Dateien
            logs_path = Path(settings.LOGS_DIR)
            if logs_path.exists():
                for file_path in iter_files(logs_path):
                    if (any(file_path.name.lower().endswith(ext) for ext in ['.log', '.txt', '.out']) 
                        and age_hours(file_path) > settings.CLEANUP_AFTER_HOURS):
                        result["logs_removed"].append({
                            "path": str(file_path),
                            "age_hours": round(age_hours(file_path), 1),
                            "size_bytes": file_path.stat().st_size if file_path.exists() else 0
                        })
            
            logger.info(f"Cleanup-Diagnose (dry_run): {len(result['uploads_removed'])} Uploads, "
                       f"{len(result['logs_removed'])} Logs würden gelöscht")
        else:
            # Führe tatsächliche Bereinigung durch
            removed_uploads = cleanup_old_uploads(settings.CLEANUP_AFTER_HOURS)
            removed_logs = cleanup_old_logs(settings.CLEANUP_AFTER_HOURS)
            
            result["uploads_removed"] = [{"path": str(p)} for p in removed_uploads]
            result["logs_removed"] = [{"path": str(p)} for p in removed_logs]
            
            logger.info(f"Manuelle Bereinigung durchgeführt: {len(removed_uploads)} Uploads, "
                       f"{len(removed_logs)} Logs gelöscht")
        
        result["summary"] = {
            "uploads_count": len(result["uploads_removed"]),
            "logs_count": len(result["logs_removed"]),
            "total_count": len(result["uploads_removed"]) + len(result["logs_removed"])
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Fehler bei Cleanup-Diagnose: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup-Diagnose fehlgeschlagen: {str(e)}")


@app.get("/diagnostics/ucanaccess")
async def ucanaccess_diagnostics():
    """UCanAccess diagnostics endpoint with file system details"""
    try:
        diagnosis = access_service.diagnose_ucanaccess()
        
        # Add additional file system info
        ucanaccess_home = os.environ.get('UCANACCESS_HOME', '/opt/ucanaccess')
        diagnosis["file_system"] = {
            "ucanaccess_home": ucanaccess_home,
            "home_exists": os.path.exists(ucanaccess_home),
            "home_readable": os.access(ucanaccess_home, os.R_OK) if os.path.exists(ucanaccess_home) else False
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "diagnosis": diagnosis
        }
    except Exception as e:
        logger.error(f"Diagnostics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Diagnostics failed: {str(e)}")


@app.get("/diagnostics/tables")
async def diagnostics_tables(file_id: str):
    """Enhanced diagnostics for table discovery in Access database"""
    try:
        # Find the database file by job ID
        job = job_manager.get_job(file_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status != JobStatus.UPLOADED:
            raise HTTPException(status_code=400, detail="File not ready for table analysis")
        
        file_path = Path(normalize_file_path(job.file_path))
        
        # File details
        file_stats = {
            "name": file_path.name,
            "size_mb": os.path.getsize(file_path) / (1024 * 1024),
            "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            "exists": os.path.exists(file_path),
            "readable": os.access(file_path, os.R_OK)
        }
        
        # Get detailed table information
        detailed_tables = await run_in_threadpool(list_tables_detailed, file_path)
        
        # Group by source
        by_source = {}
        for table in detailed_tables:
            source = table["source"]
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(table)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "file": file_stats,
            "table_discovery": {
                "total_count": len(detailed_tables),
                "by_source": {k: len(v) for k, v in by_source.items()},
                "by_type": {}
            },
            "tables": detailed_tables
        }
        
    except Exception as e:
        logger.error(f"Table diagnostics error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Table diagnostics failed: {str(e)}")


@app.get("/diagnostics/loglevel")
async def get_log_level():
    """Get current log level"""
    import logging
    current_level = logging.getLogger().level
    level_name = logging.getLevelName(current_level)
    return {
        "current_level": level_name,
        "available_levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    }


@app.post("/diagnostics/loglevel")
async def set_log_level_endpoint(level: str):
    """Set log level at runtime (for development)"""
    try:
        from .core.logging import set_log_level
        success = set_log_level(level)
        
        if success:
            return {"message": f"Log level set to {level.upper()}", "success": True}
        else:
            raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")
            
    except Exception as e:
        logger.error(f"Failed to set log level: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to set log level: {str(e)}")


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
        
        # Validate file size
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_mb}MB, actual size: {actual_mb:.1f}MB"
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Save uploaded file
        file_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}_{file.filename}")
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        # Create job with normalized path
        filename = file.filename or "unknown.accdb"
        normalized_file_path = normalize_file_path(file_path)
        job_manager.create_job(job_id, normalized_file_path, filename)
        
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
        
        # Extract tables using Access service with normalized path
        normalized_path = normalize_file_path(job.file_path)
        tables = await run_in_threadpool(access_service.get_tables, normalized_path)
        
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
            _process_conversion(
                job_id, 
                request.selected_tables, 
                request.export_format,
                bool(request.create_pivot_tables),
                bool(request.export_queries), 
                bool(request.export_schema)
            )
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


async def _process_conversion(job_id: str, selected_tables: List[str], export_format: str,
                             create_pivot_tables: bool = False,
                             export_queries: bool = False, 
                             export_schema: bool = False):
    """Background task for processing conversion with advanced options"""
    try:
        job = job_manager.get_job(job_id)
        if not job:
            return
        
        # Get data from Access database
        job_manager.update_job_progress(job_id, 10, "Reading database...")
        normalized_path = normalize_file_path(job.file_path)
        data = await run_in_threadpool(access_service.get_table_data, normalized_path, selected_tables)
        
        # Export data with advanced options
        job_manager.update_job_progress(job_id, 50, "Converting data...")
        export_files = await export_service.export_data(
            data, 
            export_format, 
            job_id,
            create_pivot_tables=create_pivot_tables,
            export_queries=export_queries,
            export_schema=export_schema,
            access_service=access_service,
            access_file_path=normalized_path
        )
        
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
        
        # Post-Job Cleanup: Remove upload files for this job_id
        try:
            cleanup_uploads_for_file_id(job_id)
        except Exception as cleanup_error:
            # Log cleanup error but don't fail the job
            logger.warning(f"Post-Job Cleanup fehlgeschlagen für job_id {job_id}: {cleanup_error}")
        
        logger.info(f"Conversion completed for job {job_id}")
        
    except ValueError as e:
        # Handle validation errors (e.g., invalid table names)
        error_msg = f"Validation error: {str(e)}"
        logger.error(f"Validation error for job {job_id}: {str(e)}")
        job_manager.update_job_status(job_id, JobStatus.FAILED)
        job_manager.update_job_progress(job_id, 0, error_msg)
    except Exception as e:
        # Handle all other errors
        error_msg = f"Conversion failed: {str(e)}"
        logger.error(f"Conversion error for job {job_id}: {str(e)}")
        job_manager.update_job_status(job_id, JobStatus.FAILED)
        job_manager.update_job_progress(job_id, 0, error_msg)


@app.on_event("startup")
async def startup_event():
    """Application startup with detailed diagnostics"""
    logger.info("Access Database Converter started")
    logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    logger.info(f"Export directory: {settings.EXPORT_DIR}")
    
    # Java diagnostics
    await _log_java_diagnostics()
    
    # UCanAccess diagnostics
    await _log_ucanaccess_diagnostics()


async def _log_java_diagnostics():
    """Log Java version and configuration"""
    try:
        import subprocess
        result = await run_in_threadpool(
            subprocess.run, 
            ["java", "-version"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            java_version = result.stderr.split('\n')[0] if result.stderr else "Unknown"
            logger.info(f"Java version: {java_version}")
        else:
            logger.error("Java not found or not working")
    except Exception as e:
        logger.error(f"Failed to check Java version: {e}")


async def _log_ucanaccess_diagnostics():
    """Log UCanAccess JAR files and configuration using the same logic as the UCanAccess service"""
    from .services.ucan import _ucan_home, _collect_ucan_jars
    
    ucanaccess_home = _ucan_home()
    logger.info(f"UCANACCESS_HOME: {ucanaccess_home}")
    
    # Use the same JAR collection logic as the UCanAccess service
    found_jars, missing_jars = _collect_ucan_jars()
    
    if missing_jars:
        logger.error("UCanAccess may not work properly without these JARs")
    else:
        logger.info("All required UCanAccess JARs found")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("Access Database Converter shutting down")
    
    # Stop periodic cleanup thread
    stop_periodic_cleanup()
    
    # Clean up temp files
    try:
        for job_id, job in job_manager.jobs.items():
            normalized_path = normalize_file_path(job.file_path)
            if os.path.exists(normalized_path):
                os.remove(normalized_path)
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
