"""Tests for Webhook API endpoints."""

import pytest


class TestWebhooks:
    """Test webhook CRUD operations."""
    
    def test_create_webhook(self, client, sample_webhook):
        """Test creating a new webhook."""
        response = client.post("/api/webhooks", json=sample_webhook)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_webhook["name"]
        assert data["url"] == sample_webhook["url"]
        assert data["event_type"] == sample_webhook["event_type"]
    
    def test_get_webhooks(self, client, sample_webhook):
        """Test listing webhooks."""
        client.post("/api/webhooks", json=sample_webhook)
        response = client.get("/api/webhooks")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
    
    def test_update_webhook(self, client, sample_webhook):
        """Test updating a webhook."""
        create_response = client.post("/api/webhooks", json=sample_webhook)
        webhook_id = create_response.json()["id"]
        
        update_data = {"name": "Updated Webhook", "is_enabled": False}
        response = client.put(f"/api/webhooks/{webhook_id}", json=update_data)
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Webhook"
        assert response.json()["is_enabled"] is False
    
    def test_delete_webhook(self, client, sample_webhook):
        """Test deleting a webhook."""
        create_response = client.post("/api/webhooks", json=sample_webhook)
        webhook_id = create_response.json()["id"]
        
        response = client.delete(f"/api/webhooks/{webhook_id}")
        assert response.status_code == 200
    
    def test_filter_by_event_type(self, client, sample_webhook):
        """Test filtering webhooks by event type."""
        client.post("/api/webhooks", json=sample_webhook)
        
        # Create another webhook with different event type
        other_webhook = {**sample_webhook, "event_type": "product.updated"}
        client.post("/api/webhooks", json=other_webhook)
        
        response = client.get("/api/webhooks?event_type=product.created")
        assert response.status_code == 200
        assert all(w["event_type"] == "product.created" for w in response.json()["items"])
    
    def test_invalid_url(self, client, sample_webhook):
        """Test that invalid URLs are rejected."""
        invalid_webhook = {**sample_webhook, "url": "not-a-url"}
        response = client.post("/api/webhooks", json=invalid_webhook)
        assert response.status_code == 422
    
    def test_get_event_types(self, client):
        """Test getting available event types."""
        response = client.get("/api/webhooks/events/types")
        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data
        assert len(data["event_types"]) > 0
