import logging
import logging.handlers
import os
import sys
from datetime import datetime

from .config import settings


def setup_logging() -> logging.Logger:
    """Setup application logging"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_SIZE,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not setup file logging: {e}")
    
    # Application logger
    app_logger = logging.getLogger("access_converter")
    
    # Log startup information
    app_logger.info(f"=== {settings.APP_NAME} v{settings.APP_VERSION} Starting ===")
    app_logger.info(f"Log level: {settings.LOG_LEVEL}")
    app_logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    app_logger.info(f"Export directory: {settings.EXPORT_DIR}")
    app_logger.info(f"Max upload size: {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB")
    app_logger.info(f"Max concurrent jobs: {settings.MAX_CONCURRENT_JOBS}")
    
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    return logging.getLogger(f"access_converter.{name}")


class AccessLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding job context"""
    
    def __init__(self, logger, job_id=None):
        self.job_id = job_id
        super().__init__(logger, {})
    
    def process(self, msg, kwargs):
        if self.job_id:
            return f"[Job {self.job_id}] {msg}", kwargs
        return msg, kwargs
