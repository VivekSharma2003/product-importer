"""Product API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models.product import Product
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, 
    ProductFilter, ProductListResponse
)

router = APIRouter()


@router.get("", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sku: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List products with filtering and pagination."""
    query = db.query(Product)
    
    # Apply filters
    if sku:
        query = query.filter(func.lower(Product.sku).contains(sku.lower()))
    if name:
        query = query.filter(func.lower(Product.name).contains(name.lower()))
    if description:
        query = query.filter(func.lower(Product.description).contains(description.lower()))
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    # Global search across multiple fields
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Product.sku).like(search_term),
                func.lower(Product.name).like(search_term),
                func.lower(Product.description).like(search_term)
            )
        )
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    products = query.order_by(Product.id.desc()).offset(offset).limit(page_size).all()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size
    
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in products],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db)):
    """Create a new product."""
    # Check for existing SKU (case-insensitive)
    existing = db.query(Product).filter(
        func.lower(Product.sku) == product_data.sku.lower()
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU '{product_data.sku}' already exists")
    
    product = Product(
        sku=product_data.sku.upper(),
        name=product_data.name,
        description=product_data.description,
        price=product_data.price,
        quantity=product_data.quantity,
        is_active=product_data.is_active
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    # Trigger webhook
    try:
        from app.tasks.webhook_sender import trigger_webhooks
        trigger_webhooks.delay("product.created", product.to_dict())
    except Exception:
        pass  # Don't fail if webhook trigger fails
    
    return ProductResponse.model_validate(product)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_data: ProductUpdate, db: Session = Depends(get_db)):
    """Update a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update only provided fields
    update_data = product_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    db.commit()
    db.refresh(product)
    
    # Trigger webhook
    try:
        from app.tasks.webhook_sender import trigger_webhooks
        trigger_webhooks.delay("product.updated", product.to_dict())
    except Exception:
        pass  # Don't fail if webhook trigger fails
    
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Delete a product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_data = product.to_dict()  # Get data before deletion
    db.delete(product)
    db.commit()
    
    # Trigger webhook
    try:
        from app.tasks.webhook_sender import trigger_webhooks
        trigger_webhooks.delay("product.deleted", product_data)
    except Exception:
        pass  # Don't fail if webhook trigger fails
    
    return {"message": "Product deleted successfully"}


@router.delete("")
def delete_all_products(confirm: bool = Query(..., description="Confirm deletion"), db: Session = Depends(get_db)):
    """Delete all products. Requires confirmation."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to delete all products")
    
    count = db.query(Product).count()
    db.query(Product).delete()
    db.commit()
    
    return {"message": f"Successfully deleted {count} products"}


@router.get("/stats/summary")
def get_product_stats(db: Session = Depends(get_db)):
    """Get product statistics."""
    total = db.query(Product).count()
    active = db.query(Product).filter(Product.is_active == True).count()
    inactive = db.query(Product).filter(Product.is_active == False).count()
    
    return {
        "total": total,
        "active": active,
        "inactive": inactive
    }
