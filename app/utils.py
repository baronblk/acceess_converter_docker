import os
import uuid
import tempfile
import shutil
from typing import Optional, List, Iterator
import logging
from pathlib import Path
import time
from datetime import datetime, timedelta

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


# ============================================================================
# CLEANUP UTILITIES
# ============================================================================

def age_hours(path: Path) -> float:
    """Berechnet das Alter einer Datei in Stunden"""
    try:
        mtime = path.stat().st_mtime
        age_seconds = time.time() - mtime
        return age_seconds / 3600.0
    except (OSError, FileNotFoundError):
        # Wenn Datei nicht existiert, als sehr alt betrachten
        return float('inf')


def iter_files(dir_path: Path) -> Iterator[Path]:
    """Iteriert über alle Dateien in einem Verzeichnis (keine Unterverzeichnisse)"""
    try:
        if dir_path.exists() and dir_path.is_dir():
            for item in dir_path.iterdir():
                if item.is_file():
                    yield item
    except (OSError, PermissionError) as e:
        logger.warning(f"Fehler beim Durchsuchen von {dir_path}: {e}")


def cleanup_uploads_for_file_id(file_id: str, upload_dir: Optional[str] = None) -> List[Path]:
    """
    Löscht alle Upload-Dateien für eine bestimmte file_id nach erfolgreichem Job.
    
    Args:
        file_id: Die ID der Datei (z.B. Job-ID oder eindeutige Datei-ID)
        upload_dir: Upload-Verzeichnis (default: aus config)
    
    Returns:
        Liste der gelöschten Dateipfade
    """
    if upload_dir is None:
        from app.core.config import settings
        upload_dir = settings.UPLOAD_DIR
    
    upload_path = Path(upload_dir)
    removed_files = []
    
    if not upload_path.exists():
        logger.warning(f"Upload-Verzeichnis existiert nicht: {upload_path}")
        return removed_files
    
    # Suche nach Dateien mit dem Muster: f"{file_id}_*.(accdb|mdb)"
    pattern_prefixes = [f"{file_id}_"]
    extensions = ['.mdb', '.accdb']
    
    for file_path in iter_files(upload_path):
        # Prüfe ob Dateiname mit file_id beginnt und richtige Erweiterung hat
        filename = file_path.name
        has_matching_prefix = any(filename.startswith(prefix) for prefix in pattern_prefixes)
        has_matching_extension = any(filename.lower().endswith(ext) for ext in extensions)
        
        if has_matching_prefix and has_matching_extension:
            try:
                file_path.unlink()
                removed_files.append(file_path)
                logger.debug(f"Upload-Datei gelöscht: {file_path}")
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Fehler beim Löschen von {file_path}: {e}")
    
    if removed_files:
        logger.info(f"Post-Job Cleanup: {len(removed_files)} Upload-Dateien für file_id '{file_id}' gelöscht")
    else:
        logger.debug(f"Post-Job Cleanup: Keine Upload-Dateien für file_id '{file_id}' gefunden")
    
    return removed_files


def cleanup_old_uploads(hours: int, upload_dir: Optional[str] = None) -> List[Path]:
    """
    Löscht alle Upload-Dateien, die älter als die angegebene Stundenanzahl sind.
    
    Args:
        hours: Maximales Alter der Dateien in Stunden
        upload_dir: Upload-Verzeichnis (default: aus config)
    
    Returns:
        Liste der gelöschten Dateipfade
    """
    if upload_dir is None:
        from app.core.config import settings
        upload_dir = settings.UPLOAD_DIR
    
    upload_path = Path(upload_dir)
    removed_files = []
    kept_count = 0
    
    if not upload_path.exists():
        logger.warning(f"Upload-Verzeichnis existiert nicht: {upload_path}")
        return removed_files
    
    for file_path in iter_files(upload_path):
        file_age = age_hours(file_path)
        
        if file_age > hours:
            try:
                file_path.unlink()
                removed_files.append(file_path)
                logger.debug(f"Alte Upload-Datei gelöscht: {file_path} (Alter: {file_age:.1f}h)")
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Fehler beim Löschen von {file_path}: {e}")
        else:
            kept_count += 1
    
    logger.info(f"Upload-Bereinigung: {len(removed_files)} Dateien gelöscht, {kept_count} behalten (Schwellwert: {hours}h)")
    return removed_files


def cleanup_old_logs(hours: int, logs_dir: Optional[str] = None) -> List[Path]:
    """
    Löscht alle Log-Dateien, die älter als die angegebene Stundenanzahl sind.
    
    Args:
        hours: Maximales Alter der Dateien in Stunden
        logs_dir: Log-Verzeichnis (default: aus config)
    
    Returns:
        Liste der gelöschten Dateipfade
    """
    if logs_dir is None:
        from app.core.config import settings
        logs_dir = settings.LOGS_DIR
    
    logs_path = Path(logs_dir)
    removed_files = []
    kept_count = 0
    
    if not logs_path.exists():
        logger.warning(f"Log-Verzeichnis existiert nicht: {logs_path}")
        return removed_files
    
    for file_path in iter_files(logs_path):
        # Nur Log-Dateien berücksichtigen (häufige Endungen)
        if not any(file_path.name.lower().endswith(ext) for ext in ['.log', '.txt', '.out']):
            continue
            
        file_age = age_hours(file_path)
        
        if file_age > hours:
            try:
                file_path.unlink()
                removed_files.append(file_path)
                logger.debug(f"Alte Log-Datei gelöscht: {file_path} (Alter: {file_age:.1f}h)")
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Fehler beim Löschen von {file_path}: {e}")
        else:
            kept_count += 1
    
    logger.info(f"Log-Bereinigung: {len(removed_files)} Dateien gelöscht, {kept_count} behalten (Schwellwert: {hours}h)")
    return removed_files
