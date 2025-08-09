from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application settings
    APP_NAME: str = "Access Database Converter"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    UPLOAD_DIR: str = "/app/data/uploads"
    EXPORT_DIR: str = "/app/data/exports"
    
    # Job settings
    MAX_CONCURRENT_JOBS: int = 3
    JOB_TIMEOUT_MINUTES: int = 30
    CLEANUP_INTERVAL_HOURS: int = 1
    MAX_JOB_AGE_HOURS: int = 24
    
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
