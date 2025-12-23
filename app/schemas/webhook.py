"""Webhook Pydantic schemas for request/response validation."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator
from enum import Enum


class EventType(str, Enum):
    """Webhook event types."""
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_DELETED = "product.deleted"
    IMPORT_STARTED = "import.started"
    IMPORT_COMPLETED = "import.completed"
    IMPORT_FAILED = "import.failed"


class WebhookBase(BaseModel):
    """Base webhook schema."""
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1, max_length=500)
    event_type: str = Field(..., min_length=1)
    is_enabled: bool = True
    secret: Optional[str] = Field(None, max_length=100)
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook."""
    pass


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    event_type: Optional[str] = None
    is_enabled: Optional[bool] = None
    secret: Optional[str] = Field(None, max_length=100)
    
    @field_validator("url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format if provided."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class WebhookResponse(BaseModel):
    """Schema for webhook response."""
    id: int
    name: str
    url: str
    event_type: str
    is_enabled: bool
    secret: Optional[str]  # Will be masked in model.to_dict()
    last_triggered_at: Optional[datetime]
    last_response_code: Optional[int]
    last_response_time_ms: Optional[int]
    failure_count: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    """Response from testing a webhook."""
    success: bool
    status_code: Optional[int]
    response_time_ms: int
    error: Optional[str]


class WebhookListResponse(BaseModel):
    """List of webhooks response."""
    items: List[WebhookResponse]
    total: int
