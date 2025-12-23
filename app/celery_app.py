"""Celery application configuration."""

from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "product_importer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.import_csv", "app.tasks.webhook_sender"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max for long imports
    worker_prefetch_multiplier=1,  # One task at a time for memory efficiency
    result_expires=86400,  # Results expire after 24 hours
)

# Task routes for different queues (optional)
celery_app.conf.task_routes = {
    "app.tasks.import_csv.*": {"queue": "csv_import"},
    "app.tasks.webhook_sender.*": {"queue": "webhooks"},
}
