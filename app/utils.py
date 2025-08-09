import os
import uuid
import tempfile
import shutil
from typing import Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_job_id() -> str:
    """Generate a unique job ID"""
    return str(uuid.uuid4())


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed_file'
    
    return filename


def validate_access_file(filename: str) -> bool:
    """Validate if file is a supported Access database"""
    if not filename:
        return False
    
    valid_extensions = ['.mdb', '.accdb']
    file_ext = '.' + filename.split('.')[-1].lower()
    return file_ext in valid_extensions


def ensure_directory(directory_path: str) -> None:
    """Ensure directory exists, create if not"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.debug(f"Directory ensured: {directory_path}")
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {str(e)}")
        raise


def cleanup_file(file_path: str) -> None:
    """Safely remove a file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"File cleaned up: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup file {file_path}: {str(e)}")


def cleanup_directory(directory_path: str) -> None:
    """Safely remove a directory and all its contents"""
    try:
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)
            logger.debug(f"Directory cleaned up: {directory_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup directory {directory_path}: {str(e)}")


def get_file_size_formatted(file_path: str) -> str:
    """Get human-readable file size"""
    try:
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except:
        return "Unknown"


def create_temp_directory() -> str:
    """Create a temporary directory"""
    return tempfile.mkdtemp()


def list_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
    """List all files in directory with specified extensions"""
    files = []
    try:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                file_ext = '.' + file.split('.')[-1].lower()
                if file_ext in extensions:
                    files.append(file_path)
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {str(e)}")
    
    return files


def is_valid_job_id(job_id: str) -> bool:
    """Validate if string is a valid UUID job ID"""
    try:
        uuid.UUID(job_id)
        return True
    except ValueError:
        return False


class FileManager:
    """Utility class for file management operations"""
    
    def __init__(self, base_upload_dir: str, base_export_dir: str):
        self.upload_dir = base_upload_dir
        self.export_dir = base_export_dir
        ensure_directory(self.upload_dir)
        ensure_directory(self.export_dir)
    
    def get_upload_path(self, job_id: str, filename: str) -> str:
        """Get the full path for an uploaded file"""
        sanitized_name = sanitize_filename(filename)
        return os.path.join(self.upload_dir, f"{job_id}_{sanitized_name}")
    
    def get_export_dir(self, job_id: str) -> str:
        """Get the export directory for a job"""
        export_path = os.path.join(self.export_dir, job_id)
        ensure_directory(export_path)
        return export_path
    
    def cleanup_job_files(self, job_id: str) -> None:
        """Clean up all files related to a job"""
        # Clean up upload files
        upload_files = list_files_by_extension(self.upload_dir, ['.mdb', '.accdb'])
        for file_path in upload_files:
            if job_id in os.path.basename(file_path):
                cleanup_file(file_path)
        
        # Clean up export directory
        export_dir = os.path.join(self.export_dir, job_id)
        cleanup_directory(export_dir)
        
        # Clean up ZIP files
        zip_files = list_files_by_extension(self.export_dir, ['.zip'])
        for file_path in zip_files:
            if job_id in os.path.basename(file_path):
                cleanup_file(file_path)
        
        logger.info(f"Cleaned up all files for job {job_id}")


def format_table_name(name: str) -> Optional[str]:
    """Format table name for display"""
    # Remove system prefixes if any
    if name.startswith('MSys'):
        return None
    
    # Replace underscores with spaces for display
    formatted = name.replace('_', ' ')
    
    # Capitalize first letter of each word
    formatted = ' '.join(word.capitalize() for word in formatted.split())
    
    return formatted
