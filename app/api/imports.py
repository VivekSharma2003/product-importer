"""Import API endpoints for CSV file uploads."""

import os
import uuid
import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import redis

from app.database import get_db
from app.config import settings
from app.models.import_job import ImportJob
from app.schemas.import_job import ImportJobResponse, ImportUploadResponse, ImportListResponse

router = APIRouter()

# Redis client for progress tracking
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


@router.post("/upload", response_model=ImportUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload a CSV file for import processing."""
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save file to disk
    file_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}.csv")
    
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create import job record
    import_job = ImportJob(
        id=job_id,
        filename=file.filename,
        status="pending"
    )
    db.add(import_job)
    db.commit()
    
    # Trigger Celery task
    try:
        from app.tasks.import_csv import import_csv_task
        import_csv_task.delay(job_id, file_path)
    except Exception as e:
        # If Celery is not available, log the error
        import_job.status = "failed"
        import_job.error_details = [{"message": f"Failed to queue task: {str(e)}"}]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to queue import task: {str(e)}")
    
    return ImportUploadResponse(
        job_id=job_id,
        message="File uploaded successfully. Processing started."
    )


@router.get("/{job_id}/status", response_model=ImportJobResponse)
def get_import_status(job_id: str, db: Session = Depends(get_db)):
    """Get the status of an import job."""
    import_job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not import_job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    # Try to get real-time progress from Redis
    progress_data = redis_client.get(f"import_progress:{job_id}")
    if progress_data:
        try:
            progress = json.loads(progress_data)
            import_job.processed_rows = progress.get("processed_rows", import_job.processed_rows)
            import_job.success_count = progress.get("success_count", import_job.success_count)
            import_job.error_count = progress.get("error_count", import_job.error_count)
            import_job.created_count = progress.get("created_count", import_job.created_count)
            import_job.updated_count = progress.get("updated_count", import_job.updated_count)
            import_job.status = progress.get("status", import_job.status)
        except json.JSONDecodeError:
            pass
    
    return ImportJobResponse.model_validate(import_job.to_dict())


@router.get("/{job_id}/stream")
async def stream_import_progress(job_id: str, db: Session = Depends(get_db)):
    """SSE endpoint for real-time import progress updates."""
    import_job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not import_job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for import progress."""
        last_data = None
        retry_count = 0
        max_retries = 600  # 10 minutes max
        
        while retry_count < max_retries:
            try:
                # Get progress from Redis
                progress_data = redis_client.get(f"import_progress:{job_id}")
                
                if progress_data and progress_data != last_data:
                    last_data = progress_data
                    yield f"data: {progress_data}\n\n"
                    
                    # Check if job is complete
                    progress = json.loads(progress_data)
                    if progress.get("status") in ["completed", "failed"]:
                        break
                
                await asyncio.sleep(0.5)  # Poll every 500ms
                retry_count += 1
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
        
        yield f"data: {json.dumps({'status': 'stream_ended'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("", response_model=ImportListResponse)
def list_imports(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """List recent import jobs."""
    import_jobs = db.query(ImportJob).order_by(ImportJob.created_at.desc()).limit(limit).all()
    
    return ImportListResponse(
        items=[ImportJobResponse.model_validate(job.to_dict()) for job in import_jobs],
        total=len(import_jobs)
    )


@router.delete("/{job_id}")
def delete_import_job(job_id: str, db: Session = Depends(get_db)):
    """Delete an import job record."""
    import_job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not import_job:
        raise HTTPException(status_code=404, detail="Import job not found")
    
    # Clean up file if exists
    file_path = os.path.join(settings.UPLOAD_DIR, f"{job_id}.csv")
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Clean up Redis progress
    redis_client.delete(f"import_progress:{job_id}")
    
    db.delete(import_job)
    db.commit()
    
    return {"message": "Import job deleted successfully"}
