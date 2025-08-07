"""
FastAPI main application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.core.config import settings
from app.core.logging import logger_setup, get_logger
from app.api.routes import router
from app.models import ErrorResponse, HealthResponse
from datetime import datetime


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Access Database Converter", app_version=settings.app_version)
    
    # TODO: Initialize Redis connection
    # TODO: Check UCanAccess JARs availability
    # TODO: Start cleanup task
    
    yield
    
    # Shutdown
    logger.info("Shutting down Access Database Converter")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Convert Microsoft Access databases to CSV, XLSX, JSON, and PDF formats",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Add request ID to all requests"""
    request_id = logger_setup.generate_request_id()
    logger_setup.set_request_context(request_id=request_id)
    
    # Add request ID to request state
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        request_id=request_id,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.debug else "An unexpected error occurred",
            request_id=request_id
        ).dict()
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        services={
            "redis": "unknown",  # TODO: Check Redis connection
            "ucanaccess": "unknown",  # TODO: Check UCanAccess availability
        }
    )


# Mount API routes
app.include_router(router, prefix="/api")

# Serve static files (for frontend)
if settings.app_env != "development":
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )
