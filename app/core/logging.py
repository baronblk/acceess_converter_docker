import logging
import logging.handlers
import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from .config import settings


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create the log entry as a dictionary
        log_entry = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        request_id = getattr(record, 'request_id', None)
        if request_id is not None:
            log_entry['request_id'] = request_id
            
        job_id = getattr(record, 'job_id', None)
        if job_id is not None:
            log_entry['job_id'] = job_id
            
        file_path = getattr(record, 'file_path', None)
        if file_path is not None:
            log_entry['file_path'] = file_path
            
        duration = getattr(record, 'duration', None)
        if duration is not None:
            log_entry['duration_ms'] = duration
        
        return json.dumps(log_entry, ensure_ascii=False)


class ReadableFormatter(logging.Formatter):
    """Human-readable formatter for console output"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base format
        formatted = super().format(record)
        
        # Add extra context if available
        extras = []
        request_id = getattr(record, 'request_id', None)
        if request_id is not None:
            extras.append(f"req_id={request_id[:8]}")
            
        job_id = getattr(record, 'job_id', None)
        if job_id is not None:
            extras.append(f"job={job_id}")
            
        duration = getattr(record, 'duration', None)
        if duration is not None:
            extras.append(f"duration={duration}ms")
        
        if extras:
            formatted += f" [{', '.join(extras)}]"
            
        return formatted


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
    
    # Create formatters based on configuration
    if settings.LOG_JSON:
        console_formatter = JSONFormatter(datefmt='%Y-%m-%dT%H:%M:%S')
        file_formatter = JSONFormatter(datefmt='%Y-%m-%dT%H:%M:%S')
    else:
        console_formatter = ReadableFormatter(
            fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler - always uses the configured log level for container logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    console_handler.setFormatter(console_formatter)
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
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"Could not setup file logging: {e}")
    
    # Application logger
    app_logger = logging.getLogger("access_converter")
    
    # Log startup information
    app_logger.info(f"=== {settings.APP_NAME} v{settings.APP_VERSION} Starting ===")
    app_logger.info(f"Log level: {settings.LOG_LEVEL}")
    app_logger.info(f"Log format: {'JSON' if settings.LOG_JSON else 'Human-readable'}")
    app_logger.info(f"Upload directory: {settings.UPLOAD_DIR}")
    app_logger.info(f"Export directory: {settings.EXPORT_DIR}")
    app_logger.info(f"Max upload size: {settings.MAX_UPLOAD_SIZE / (1024*1024):.1f}MB")
    app_logger.info(f"Max concurrent jobs: {settings.MAX_CONCURRENT_JOBS}")
    
    return app_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    return logging.getLogger(f"access_converter.{name}")


def set_log_level(level: str) -> bool:
    """Set log level at runtime"""
    try:
        log_level = getattr(logging, level.upper())
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Update console handler level as well
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                handler.setLevel(log_level)
                
        app_logger = logging.getLogger("access_converter")
        app_logger.info(f"Log level changed to: {level.upper()}")
        return True
    except AttributeError:
        return False


class AccessLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding context"""
    
    def __init__(self, logger, extra=None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})
        
        # Add context from adapter's extra
        if self.extra:
            for key, value in self.extra.items():
                extra[key] = value
            
        kwargs['extra'] = extra
        return msg, kwargs


class RequestLoggerAdapter(AccessLoggerAdapter):
    """Logger adapter for request context"""
    
    def __init__(self, logger, request_id: str):
        super().__init__(logger, {'request_id': request_id})


class JobLoggerAdapter(AccessLoggerAdapter):
    """Logger adapter for job context"""
    
    def __init__(self, logger, job_id: str, file_path: Optional[str] = None):
        extra = {'job_id': job_id}
        if file_path:
            extra['file_path'] = file_path
        super().__init__(logger, extra)
