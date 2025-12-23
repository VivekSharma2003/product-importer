"""Webhook API endpoints."""

import time
import httpx
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.webhook import Webhook
from app.schemas.webhook import (
    WebhookCreate, WebhookUpdate, WebhookResponse,
    WebhookListResponse, WebhookTestResponse
)

router = APIRouter()


@router.get("", response_model=WebhookListResponse)
def list_webhooks(
    event_type: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """List all webhooks with optional filtering."""
    query = db.query(Webhook)
    
    if event_type:
        query = query.filter(Webhook.event_type == event_type)
    if is_enabled is not None:
        query = query.filter(Webhook.is_enabled == is_enabled)
    
    webhooks = query.order_by(Webhook.id.desc()).all()
    
    return WebhookListResponse(
        items=[WebhookResponse.model_validate(w.to_dict()) for w in webhooks],
        total=len(webhooks)
    )


@router.post("", response_model=WebhookResponse, status_code=201)
def create_webhook(webhook_data: WebhookCreate, db: Session = Depends(get_db)):
    """Create a new webhook."""
    webhook = Webhook(
        name=webhook_data.name,
        url=webhook_data.url,
        event_type=webhook_data.event_type,
        is_enabled=webhook_data.is_enabled,
        secret=webhook_data.secret
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return WebhookResponse.model_validate(webhook.to_dict())


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Get a webhook by ID."""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return WebhookResponse.model_validate(webhook.to_dict())


@router.put("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(webhook_id: int, webhook_data: WebhookUpdate, db: Session = Depends(get_db)):
    """Update a webhook."""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Update only provided fields
    update_data = webhook_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    
    db.commit()
    db.refresh(webhook)
    
    return WebhookResponse.model_validate(webhook.to_dict())


@router.delete("/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Delete a webhook."""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
    
    return {"message": "Webhook deleted successfully"}


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
def test_webhook(webhook_id: int, db: Session = Depends(get_db)):
    """Test a webhook by sending a test payload."""
    webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Prepare test payload
    test_payload = {
        "event": "test",
        "webhook_id": webhook.id,
        "webhook_name": webhook.name,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "This is a test webhook from Product Importer"
    }
    
    start_time = time.time()
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                webhook.url,
                json=test_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": "test"
                }
            )
        
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Update webhook with last test results
        webhook.last_triggered_at = datetime.utcnow()
        webhook.last_response_code = response.status_code
        webhook.last_response_time_ms = response_time_ms
        
        if response.status_code >= 400:
            webhook.failure_count += 1
        else:
            webhook.failure_count = 0
        
        db.commit()
        
        return WebhookTestResponse(
            success=response.status_code < 400,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            error=None if response.status_code < 400 else f"HTTP {response.status_code}"
        )
        
    except httpx.TimeoutException:
        response_time_ms = int((time.time() - start_time) * 1000)
        webhook.failure_count += 1
        db.commit()
        
        return WebhookTestResponse(
            success=False,
            status_code=None,
            response_time_ms=response_time_ms,
            error="Request timed out"
        )
        
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        webhook.failure_count += 1
        db.commit()
        
        return WebhookTestResponse(
            success=False,
            status_code=None,
            response_time_ms=response_time_ms,
            error=str(e)
        )


@router.get("/events/types")
def get_event_types():
    """Get available webhook event types."""
    return {
        "event_types": [
            {"value": "product.created", "label": "Product Created"},
            {"value": "product.updated", "label": "Product Updated"},
            {"value": "product.deleted", "label": "Product Deleted"},
            {"value": "import.started", "label": "Import Started"},
            {"value": "import.completed", "label": "Import Completed"},
            {"value": "import.failed", "label": "Import Failed"},
        ]
    }
