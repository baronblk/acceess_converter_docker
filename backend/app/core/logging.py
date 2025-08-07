"""
Structured logging configuration
"""
import logging
import logging.handlers
import sys
import uuid
from pathlib import Path
from typing import Any, Dict

import structlog

from app.core.config import settings


class RequestContextFilter(logging.Filter):
    """Add request context to log records"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add request_id if not present
        if not hasattr(record, 'request_id'):
            record.request_id = getattr(self, '_request_id', 'no-request')
        
        # Add job_id if not present  
        if not hasattr(record, 'job_id'):
            record.job_id = getattr(self, '_job_id', 'no-job')
            
        return True
    
    def set_request_id(self, request_id: str):
        """Set request ID for current context"""
        self._request_id = request_id
    
    def set_job_id(self, job_id: str):
        """Set job ID for current context"""
        self._job_id = job_id


class LoggerSetup:
    """Setup structured logging for the application"""
    
    def __init__(self):
        self.request_filter = RequestContextFilter()
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging with structured output"""
        
        # Create logs directory
        logs_dir = Path(settings.logs_path)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler (INFO level)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s | req:%(request_id)s | job:%(job_id)s"
        )
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(self.request_filter)
        
        # File handler (DEBUG level, rotating)
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "app.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s | req:%(request_id)s | job:%(job_id)s"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(self.request_filter)
        
        # Add handlers to root logger
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        # Configure specific loggers
        self._configure_specific_loggers()
        
        # Configure structlog
        self._configure_structlog()
    
    def _configure_specific_loggers(self):
        """Configure specific logger levels"""
        
        # Application logger
        app_logger = logging.getLogger("accdb_web")
        app_logger.setLevel(logging.DEBUG if settings.debug else logging.INFO)
        
        # Reduce noise from third-party libraries
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("rq.worker").setLevel(logging.INFO)
        
    def _configure_structlog(self):
        """Configure structlog for structured logging"""
        
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.JSONRenderer() if settings.app_env == "production" 
                else structlog.dev.ConsoleRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.DEBUG if settings.debug else logging.INFO
            ),
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def get_logger(self, name: str = "accdb_web") -> structlog.BoundLogger:
        """Get a configured logger instance"""
        return structlog.get_logger(name)
    
    def set_request_context(self, request_id: str = None, job_id: str = None):
        """Set context for current request/job"""
        if request_id:
            self.request_filter.set_request_id(request_id)
        if job_id:
            self.request_filter.set_job_id(job_id)
    
    def generate_request_id(self) -> str:
        """Generate a unique request ID"""
        return str(uuid.uuid4())[:8]
    
    def generate_job_id(self) -> str:
        """Generate a unique job ID"""
        return str(uuid.uuid4())


# Global logger setup instance
logger_setup = LoggerSetup()

# Convenience function to get logger
def get_logger(name: str = "accdb_web") -> structlog.BoundLogger:
    """Get application logger"""
    return logger_setup.get_logger(name)
