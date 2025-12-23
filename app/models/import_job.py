"""Import job model for tracking CSV import progress."""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class ImportJob(Base):
    """Import job for tracking CSV file processing."""
    
    __tablename__ = "import_jobs"
    
    id = Column(String(36), primary_key=True)  # UUID
    filename = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    # Status values: pending, parsing, validating, importing, completed, failed
    
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    
    error_details = Column(JSON, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "status": self.status,
            "total_rows": self.total_rows,
            "processed_rows": self.processed_rows,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "created_count": self.created_count,
            "updated_count": self.updated_count,
            "error_details": self.error_details,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "progress_percentage": round(
                (self.processed_rows / self.total_rows * 100) if self.total_rows > 0 else 0, 2
            ),
        }
