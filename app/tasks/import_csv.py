"""CSV Import Celery task for processing large CSV files."""

import csv
import json
import os
from datetime import datetime
from typing import List, Dict, Any
import redis
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from decimal import Decimal, InvalidOperation

from app.celery_app import celery_app
from app.config import settings
from app.database import get_db_context
from app.models.product import Product
from app.models.import_job import ImportJob

# Redis client for progress updates
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def update_progress(job_id: str, data: Dict[str, Any]):
    """Update progress in Redis for real-time tracking."""
    redis_client.set(
        f"import_progress:{job_id}",
        json.dumps(data),
        ex=3600  # Expire after 1 hour
    )


def parse_csv_row(row: Dict[str, str], row_num: int) -> Dict[str, Any]:
    """Parse and validate a CSV row."""
    errors = []
    
    # Required fields
    sku = row.get("sku", "").strip()
    name = row.get("name", "").strip()
    
    if not sku:
        errors.append("SKU is required")
    if not name:
        errors.append("Name is required")
    
    # Optional fields with type conversion
    description = row.get("description", "").strip() or None
    
    # Parse price
    price = None
    price_str = row.get("price", "").strip()
    if price_str:
        try:
            price = Decimal(price_str)
            if price < 0:
                errors.append("Price cannot be negative")
        except (InvalidOperation, ValueError):
            errors.append(f"Invalid price format: {price_str}")
    
    # Parse quantity
    quantity = 0
    quantity_str = row.get("quantity", "").strip()
    if quantity_str:
        try:
            quantity = int(quantity_str)
            if quantity < 0:
                errors.append("Quantity cannot be negative")
        except ValueError:
            errors.append(f"Invalid quantity format: {quantity_str}")
    
    if errors:
        return {"valid": False, "errors": errors, "row": row_num}
    
    return {
        "valid": True,
        "data": {
            "sku": sku.upper(),  # Normalize SKU to uppercase
            "name": name,
            "description": description,
            "price": price,
            "quantity": quantity,
            "is_active": True  # Default to active
        }
    }


def count_csv_rows(file_path: str) -> int:
    """Count total rows in CSV file (excluding header)."""
    with open(file_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # Subtract header row


@celery_app.task(bind=True, max_retries=3)
def import_csv_task(self, job_id: str, file_path: str):
    """
    Process a CSV file and import products into the database.
    
    Optimizations for large files:
    - Streaming CSV reading (memory efficient)
    - Bulk upsert operations
    - Progress tracking via Redis
    - Chunked processing
    """
    
    with get_db_context() as db:
        # Get import job
        import_job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not import_job:
            return {"error": "Import job not found"}
        
        try:
            # Update status to parsing
            import_job.status = "parsing"
            import_job.started_at = datetime.utcnow()
            db.commit()
            
            update_progress(job_id, {
                "status": "parsing",
                "message": "Counting rows in CSV file...",
                "processed_rows": 0,
                "total_rows": 0,
                "success_count": 0,
                "error_count": 0,
                "created_count": 0,
                "updated_count": 0
            })
            
            # Count total rows
            total_rows = count_csv_rows(file_path)
            import_job.total_rows = total_rows
            db.commit()
            
            update_progress(job_id, {
                "status": "validating",
                "message": f"Processing {total_rows:,} products...",
                "processed_rows": 0,
                "total_rows": total_rows,
                "success_count": 0,
                "error_count": 0,
                "created_count": 0,
                "updated_count": 0
            })
            
            # Process CSV file
            processed_rows = 0
            success_count = 0
            error_count = 0
            created_count = 0
            updated_count = 0
            error_details = []
            batch = []
            
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                    parsed = parse_csv_row(row, row_num)
                    
                    if parsed["valid"]:
                        batch.append(parsed["data"])
                        success_count += 1
                    else:
                        error_count += 1
                        if len(error_details) < 100:  # Limit stored errors
                            error_details.append({
                                "row": row_num,
                                "errors": parsed["errors"],
                                "sku": row.get("sku", "")
                            })
                    
                    processed_rows += 1
                    
                    # Process batch when it reaches chunk size
                    if len(batch) >= settings.CHUNK_SIZE:
                        created, updated = upsert_products(db, batch)
                        created_count += created
                        updated_count += updated
                        batch = []
                    
                    # Update progress periodically
                    if processed_rows % settings.PROGRESS_UPDATE_INTERVAL == 0:
                        import_job.status = "importing"
                        import_job.processed_rows = processed_rows
                        import_job.success_count = success_count
                        import_job.error_count = error_count
                        import_job.created_count = created_count
                        import_job.updated_count = updated_count
                        db.commit()
                        
                        update_progress(job_id, {
                            "status": "importing",
                            "message": f"Processing row {processed_rows:,} of {total_rows:,}...",
                            "processed_rows": processed_rows,
                            "total_rows": total_rows,
                            "success_count": success_count,
                            "error_count": error_count,
                            "created_count": created_count,
                            "updated_count": updated_count,
                            "progress_percentage": round(processed_rows / total_rows * 100, 2)
                        })
            
            # Process remaining batch
            if batch:
                created, updated = upsert_products(db, batch)
                created_count += created
                updated_count += updated
            
            # Mark as completed
            import_job.status = "completed"
            import_job.processed_rows = processed_rows
            import_job.success_count = success_count
            import_job.error_count = error_count
            import_job.created_count = created_count
            import_job.updated_count = updated_count
            import_job.error_details = error_details if error_details else None
            import_job.completed_at = datetime.utcnow()
            db.commit()
            
            # Final progress update
            update_progress(job_id, {
                "status": "completed",
                "message": f"Import completed! {success_count:,} products processed.",
                "processed_rows": processed_rows,
                "total_rows": total_rows,
                "success_count": success_count,
                "error_count": error_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "progress_percentage": 100
            })
            
            # Trigger webhooks for import.completed
            from app.tasks.webhook_sender import trigger_webhooks
            trigger_webhooks.delay("import.completed", {
                "job_id": job_id,
                "total_rows": total_rows,
                "success_count": success_count,
                "error_count": error_count,
                "created_count": created_count,
                "updated_count": updated_count
            })
            
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            return {
                "status": "completed",
                "processed_rows": processed_rows,
                "success_count": success_count,
                "error_count": error_count,
                "created_count": created_count,
                "updated_count": updated_count
            }
            
        except Exception as e:
            # Mark as failed
            import_job.status = "failed"
            import_job.error_details = [{"message": str(e)}]
            import_job.completed_at = datetime.utcnow()
            db.commit()
            
            update_progress(job_id, {
                "status": "failed",
                "message": f"Import failed: {str(e)}",
                "error": str(e),
                "processed_rows": import_job.processed_rows,
                "total_rows": import_job.total_rows,
                "success_count": import_job.success_count,
                "error_count": import_job.error_count
            })
            
            # Clean up uploaded file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            raise


def upsert_products(db, products: List[Dict[str, Any]]) -> tuple:
    """
    Bulk upsert products using PostgreSQL ON CONFLICT.
    Returns tuple of (created_count, updated_count).
    """
    if not products:
        return 0, 0
    
    # Get existing SKUs to determine created vs updated
    skus = [p["sku"] for p in products]
    existing_skus = set(
        row[0] for row in db.query(Product.sku).filter(
            func.upper(Product.sku).in_(skus)
        ).all()
    )
    
    created_count = 0
    updated_count = 0
    
    for product_data in products:
        if product_data["sku"] in existing_skus:
            updated_count += 1
        else:
            created_count += 1
    
    # Prepare upsert statement
    stmt = insert(Product).values(products)
    stmt = stmt.on_conflict_do_update(
        index_elements=["sku"],
        set_={
            "name": stmt.excluded.name,
            "description": stmt.excluded.description,
            "price": stmt.excluded.price,
            "quantity": stmt.excluded.quantity,
            "updated_at": datetime.utcnow()
        }
    )
    
    db.execute(stmt)
    db.commit()
    
    return created_count, updated_count
