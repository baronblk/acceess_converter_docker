from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"
    JSON = "json"
    PDF = "pdf"


class ConversionRequest(BaseModel):
    selected_tables: List[str]
    export_format: ExportFormat
    # Erweiterte Export-Optionen
    create_pivot_tables: Optional[bool] = False
    export_queries: Optional[bool] = False
    export_schema: Optional[bool] = False


class JobResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    message: str
    progress: Optional[int] = 0


class TableInfo(BaseModel):
    name: str
    row_count: Optional[int] = None
    column_count: Optional[int] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str
    created_at: str
    download_ready: bool = False
