"""Webhook sender Celery task for sending notifications to configured webhooks."""

import json
import time
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
import httpx

from app.celery_app import celery_app
from app.database import get_db_context
from app.models.webhook import Webhook


def generate_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_webhook(self, webhook_id: int, event_type: str, payload: Dict[str, Any]):
    """
    Send a webhook notification.
    
    Implements retry logic and signature generation.
    """
    with get_db_context() as db:
        webhook = db.query(Webhook).filter(Webhook.id == webhook_id).first()
        
        if not webhook:
            return {"error": "Webhook not found"}
        
        if not webhook.is_enabled:
            return {"skipped": "Webhook is disabled"}
        
        # Prepare payload
        full_payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        }
        payload_json = json.dumps(full_payload)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            "X-Webhook-Timestamp": datetime.utcnow().isoformat()
        }
        
        # Add signature if secret is configured
        if webhook.secret:
            signature = generate_signature(payload_json, webhook.secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        start_time = time.time()
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers
                )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Update webhook status
            webhook.last_triggered_at = datetime.utcnow()
            webhook.last_response_code = response.status_code
            webhook.last_response_time_ms = response_time_ms
            
            if response.status_code >= 400:
                webhook.failure_count += 1
                db.commit()
                
                # Retry on server errors
                if response.status_code >= 500:
                    raise self.retry(
                        exc=Exception(f"Server error: {response.status_code}"),
                        countdown=60 * (self.request.retries + 1)  # Exponential backoff
                    )
            else:
                webhook.failure_count = 0
                db.commit()
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms
            }
            
        except httpx.TimeoutException:
            webhook.failure_count += 1
            db.commit()
            
            raise self.retry(
                exc=Exception("Request timed out"),
                countdown=60 * (self.request.retries + 1)
            )
            
        except httpx.RequestError as e:
            webhook.failure_count += 1
            db.commit()
            
            raise self.retry(
                exc=e,
                countdown=60 * (self.request.retries + 1)
            )


@celery_app.task
def trigger_webhooks(event_type: str, payload: Dict[str, Any]):
    """
    Trigger all enabled webhooks for a specific event type.
    """
    with get_db_context() as db:
        webhooks = db.query(Webhook).filter(
            Webhook.event_type == event_type,
            Webhook.is_enabled == True
        ).all()
        
        triggered_count = 0
        for webhook in webhooks:
            send_webhook.delay(webhook.id, event_type, payload)
            triggered_count += 1
        
        return {"triggered_webhooks": triggered_count}
