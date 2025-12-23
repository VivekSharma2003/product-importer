"""API routes package."""

from fastapi import APIRouter
from app.api.products import router as products_router
from app.api.webhooks import router as webhooks_router
from app.api.imports import router as imports_router

# Main API router
api_router = APIRouter(prefix="/api")

# Include sub-routers
api_router.include_router(products_router, prefix="/products", tags=["Products"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(imports_router, prefix="/imports", tags=["Imports"])
