"""Webhook model for storing webhook configurations."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class Webhook(Base):
    """Webhook configuration for external notifications."""
    
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    event_type = Column(String(50), nullable=False, index=True)
    # Event types: product.created, product.updated, product.deleted, import.completed
    is_enabled = Column(Boolean, default=True, index=True)
    secret = Column(String(100), nullable=True)  # Optional HMAC secret
    last_triggered_at = Column(DateTime, nullable=True)
    last_response_code = Column(Integer, nullable=True)
    last_response_time_ms = Column(Integer, nullable=True)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "event_type": self.event_type,
            "is_enabled": self.is_enabled,
            "secret": "***" if self.secret else None,  # Mask secret
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "last_response_code": self.last_response_code,
            "last_response_time_ms": self.last_response_time_ms,
            "failure_count": self.failure_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
