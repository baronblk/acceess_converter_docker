"""
Utility functions for file handling, validation, and helpers
"""
import os
import re
import shutil
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import uuid

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_file_id() -> str:
    """Generate a unique file identifier"""
    return str(uuid.uuid4())


def generate_job_id() -> str:
    """Generate a unique job identifier"""
    return str(uuid.uuid4())


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and invalid characters"""
    # Remove directory traversal attempts
    filename = os.path.basename(filename)
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    return filename


def get_safe_path(base_path: str, filename: str) -> Path:
    """Get a safe file path within the base directory"""
    base = Path(base_path).resolve()
    safe_filename = sanitize_filename(filename)
    target_path = (base / safe_filename).resolve()
    
    # Ensure the target path is within the base directory
    if not str(target_path).startswith(str(base)):
        raise ValueError("Invalid file path")
    
    return target_path


def ensure_unique_filename(file_path: Path) -> Path:
    """Ensure filename is unique by adding a counter if needed"""
    if not file_path.exists():
        return file_path
    
    stem = file_path.stem
    suffix = file_path.suffix
    parent = file_path.parent
    counter = 1
    
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate if file has an allowed extension"""
    if not filename:
        return False
    
    file_ext = Path(filename).suffix.lower()
    return file_ext in [ext.lower() for ext in allowed_extensions]


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in megabytes"""
    if not file_path.exists():
        return 0.0
    
    size_bytes = file_path.stat().st_size
    return size_bytes / (1024 * 1024)


def create_zip_archive(source_dir: Path, zip_path: Path, include_pattern: str = "*") -> bool:
    """Create a ZIP archive from files in a directory"""
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_dir.glob(include_pattern):
                if file_path.is_file():
                    # Add file to ZIP with relative path
                    arcname = file_path.relative_to(source_dir)
                    zipf.write(file_path, arcname)
        
        logger.info("ZIP archive created", zip_path=str(zip_path), source_dir=str(source_dir))
        return True
        
    except Exception as e:
        logger.error("Failed to create ZIP archive", error=str(e), zip_path=str(zip_path))
        return False


def cleanup_old_files(directory: Path, max_age_hours: int = 24) -> int:
    """Clean up files older than specified hours"""
    if not directory.exists():
        return 0
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    deleted_count = 0
    
    try:
        for file_path in directory.iterdir():
            if file_path.is_file():
                # Check file modification time
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug("Deleted old file", file_path=str(file_path))
            
            elif file_path.is_dir():
                # Recursively clean subdirectories
                sub_deleted = cleanup_old_files(file_path, max_age_hours)
                deleted_count += sub_deleted
                
                # Remove empty directories
                try:
                    if not any(file_path.iterdir()):
                        file_path.rmdir()
                        logger.debug("Deleted empty directory", dir_path=str(file_path))
                except OSError:
                    pass  # Directory not empty or other error
    
    except Exception as e:
        logger.error("Error during cleanup", directory=str(directory), error=str(e))
    
    if deleted_count > 0:
        logger.info("Cleanup completed", directory=str(directory), deleted_files=deleted_count)
    
    return deleted_count


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_content_type(file_path: Path) -> str:
    """Get MIME content type for file"""
    extension = file_path.suffix.lower()
    
    content_types = {
        '.csv': 'text/csv',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.json': 'application/json',
        '.pdf': 'application/pdf',
        '.zip': 'application/zip',
        '.accdb': 'application/x-msaccess',
        '.mdb': 'application/x-msaccess'
    }
    
    return content_types.get(extension, 'application/octet-stream')


def create_directory_structure():
    """Create necessary directory structure"""
    directories = [
        Path(settings.upload_path),
        Path(settings.export_path),
        Path(settings.logs_path)
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.debug("Directory ensured", path=str(directory))


def get_available_disk_space(path: Path) -> int:
    """Get available disk space in bytes"""
    try:
        stat = shutil.disk_usage(path)
        return stat.free
    except Exception as e:
        logger.error("Failed to get disk space", path=str(path), error=str(e))
        return 0


def check_disk_space(required_mb: float, path: Path = None) -> bool:
    """Check if enough disk space is available"""
    if path is None:
        path = Path(settings.upload_path)
    
    available_bytes = get_available_disk_space(path)
    required_bytes = required_mb * 1024 * 1024
    
    return available_bytes >= required_bytes
