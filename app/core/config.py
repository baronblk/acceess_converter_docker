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

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    APP_NAME: str = "Access Database Converter"
    APP_VERSION: str = "2.2.1"
    DEBUG: bool = False
    
    # File upload settings - aus Umgebungsvariablen
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # Standard: 100MB, überschreibbar via ENV
    UPLOAD_DIR: str = "/app/data/uploads"
    EXPORT_DIR: str = "/app/data/exports"
    
    # Job settings - aus Umgebungsvariablen
    MAX_CONCURRENT_JOBS: int = 3  # Überschreibbar via ENV
    JOB_TIMEOUT_MINUTES: int = 30
    CLEANUP_INTERVAL_HOURS: int = 1
    MAX_JOB_AGE_HOURS: int = 24
    
    # Erweiterte Konfiguration - neue ENV-Variablen
    MAX_TABLES_PER_DB: int = 100
    TEMP_DIR_SIZE_LIMIT: int = 1024 * 1024 * 1024  # 1GB
    WORKER_TIMEOUT: int = 300  # 5 Minuten
    CLEANUP_INTERVAL_MINUTES: int = 60  # Bereinigung in Minuten
    
    # Cleanup settings
    CLEANUP_AFTER_HOURS: int = 24  # Delete files older than X hours
    LOGS_DIR: str = "/app/logs"
    
    # Database settings
    ALLOWED_EXTENSIONS: list = [".mdb", ".accdb"]
    
    # Java/UCanAccess settings
    JAVA_HEAP_SIZE: str = "1024m"
    UCANACCESS_CLASSPATH: Optional[str] = None
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    LOG_FILE: str = "/app/logs/app.log"
    LOG_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()
