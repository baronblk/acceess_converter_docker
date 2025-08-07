"""
Application configuration settings
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # App Settings
    app_name: str = "Access Database Converter"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File Upload Settings
    max_upload_mb: int = 200
    allowed_extensions: List[str] = [".accdb", ".mdb"]
    upload_path: str = "./data/uploads"
    export_path: str = "./data/exports"
    logs_path: str = "./data/logs"
    
    # Redis/RQ Settings
    redis_url: str = "redis://localhost:6379/0"
    job_timeout: int = 3600  # 1 hour
    
    # UCanAccess Settings
    ucanaccess_path: str = "/opt/ucanaccess"
    java_classpath: str = ""
    
    # Cleanup Settings
    cleanup_after_hours: int = 24
    
    # Security
    secret_key: str = "your-secret-key-here"
    auth_token: str = ""  # Optional authentication token
    
    # CORS Settings
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Build Java classpath for UCanAccess
        if os.path.exists(self.ucanaccess_path):
            jar_files = [
                "ucanaccess-5.0.1.jar",
                "lib/commons-lang3-3.8.1.jar", 
                "lib/commons-logging-1.2.jar",
                "lib/hsqldb-2.5.0.jar",
                "lib/jackcess-4.0.2.jar"
            ]
            self.java_classpath = os.pathsep.join([
                os.path.join(self.ucanaccess_path, jar) for jar in jar_files
            ])
        
        # Ensure directories exist
        for path in [self.upload_path, self.export_path, self.logs_path]:
            os.makedirs(path, exist_ok=True)


# Global settings instance
settings = Settings()
