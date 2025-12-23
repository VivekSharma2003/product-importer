"""Import job Pydantic schemas for request/response validation."""

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel


class ImportJobResponse(BaseModel):
    """Schema for import job response."""
    id: str
    filename: str
    status: str
    total_rows: int
    processed_rows: int
    success_count: int
    error_count: int
    created_count: int
    updated_count: int
    error_details: Optional[List[Any]]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: Optional[datetime]
    progress_percentage: float
    
    class Config:
        from_attributes = True


class ImportUploadResponse(BaseModel):
    """Response from initiating a CSV import."""
    job_id: str
    message: str


class ImportListResponse(BaseModel):
    """List of import jobs response."""
    items: List[ImportJobResponse]
    total: int
