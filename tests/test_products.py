"""Tests for Product API endpoints."""

import pytest


class TestProducts:
    """Test product CRUD operations."""
    
    def test_create_product(self, client, sample_product):
        """Test creating a new product."""
        response = client.post("/api/products", json=sample_product)
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == sample_product["sku"].upper()
        assert data["name"] == sample_product["name"]
        assert data["id"] is not None
    
    def test_create_duplicate_sku(self, client, sample_product):
        """Test that duplicate SKUs are rejected."""
        client.post("/api/products", json=sample_product)
        response = client.post("/api/products", json=sample_product)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_get_products(self, client, sample_product):
        """Test listing products."""
        client.post("/api/products", json=sample_product)
        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
    
    def test_get_product_by_id(self, client, sample_product):
        """Test getting a product by ID."""
        create_response = client.post("/api/products", json=sample_product)
        product_id = create_response.json()["id"]
        
        response = client.get(f"/api/products/{product_id}")
        assert response.status_code == 200
        assert response.json()["id"] == product_id
    
    def test_get_nonexistent_product(self, client):
        """Test getting a product that doesn't exist."""
        response = client.get("/api/products/99999")
        assert response.status_code == 404
    
    def test_update_product(self, client, sample_product):
        """Test updating a product."""
        create_response = client.post("/api/products", json=sample_product)
        product_id = create_response.json()["id"]
        
        update_data = {"name": "Updated Product Name", "price": 29.99}
        response = client.put(f"/api/products/{product_id}", json=update_data)
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Product Name"
        assert response.json()["price"] == 29.99
    
    def test_delete_product(self, client, sample_product):
        """Test deleting a product."""
        create_response = client.post("/api/products", json=sample_product)
        product_id = create_response.json()["id"]
        
        response = client.delete(f"/api/products/{product_id}")
        assert response.status_code == 200
        
        # Verify it's deleted
        get_response = client.get(f"/api/products/{product_id}")
        assert get_response.status_code == 404
    
    def test_bulk_delete_without_confirm(self, client):
        """Test that bulk delete requires confirmation."""
        response = client.delete("/api/products")
        assert response.status_code == 422  # Missing confirm parameter
    
    def test_bulk_delete_with_confirm(self, client, sample_product):
        """Test bulk delete with confirmation."""
        client.post("/api/products", json=sample_product)
        response = client.delete("/api/products?confirm=true")
        assert response.status_code == 200
        
        # Verify all deleted
        list_response = client.get("/api/products")
        assert list_response.json()["total"] == 0
    
    def test_filter_by_status(self, client, sample_product):
        """Test filtering products by active status."""
        # Create active product
        client.post("/api/products", json=sample_product)
        
        # Create inactive product
        inactive_product = {**sample_product, "sku": "TEST-002", "is_active": False}
        client.post("/api/products", json=inactive_product)
        
        # Filter active only
        response = client.get("/api/products?is_active=true")
        assert response.status_code == 200
        assert all(p["is_active"] for p in response.json()["items"])
    
    def test_search_products(self, client, sample_product):
        """Test searching products."""
        client.post("/api/products", json=sample_product)
        
        response = client.get(f"/api/products?search={sample_product['name'][:4]}")
        assert response.status_code == 200
        assert response.json()["total"] >= 1
    
    def test_pagination(self, client, sample_product):
        """Test product pagination."""
        # Create multiple products
        for i in range(5):
            product = {**sample_product, "sku": f"TEST-{i:03d}"}
            client.post("/api/products", json=product)
        
        # Get first page
        response = client.get("/api/products?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_pages"] == 3
