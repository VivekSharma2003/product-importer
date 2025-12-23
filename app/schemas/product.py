"""Product Pydantic schemas for request/response validation."""

from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProductBase(BaseModel):
    """Base product schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    quantity: Optional[int] = Field(0, ge=0)
    is_active: bool = True


class ProductCreate(ProductBase):
    """Schema for creating a product."""
    sku: str = Field(..., min_length=1, max_length=100)
    
    @field_validator("sku")
    @classmethod
    def sku_must_be_valid(cls, v: str) -> str:
        """Validate and normalize SKU."""
        return v.strip().upper()


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    quantity: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: int
    sku: str
    name: str
    description: Optional[str]
    price: Optional[float]
    quantity: int
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProductFilter(BaseModel):
    """Schema for filtering products."""
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
