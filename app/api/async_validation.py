"""
Async validation endpoints using Celery for background processing
Prevents blocking the main API when processing heavy validation tasks
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Optional, Annotated, Dict, Any
from pydantic import BaseModel
from app.api.v1.deps import get_current_user_from_jwt
from app.db.models import User as UserModel
from app.verification.registry import get_verification_config
from app.logging_config import get_logger
import tempfile
import os
import json

logger = get_logger(__name__)

router = APIRouter()


class AsyncValidationResponse(BaseModel):
    """Response for async validation request"""
    task_id: str
    status: str
    message: str


class TaskStatusResponse(BaseModel):
    """Response for task status check"""
    task_id: str
    status: str
    progress: Optional[int] = None
    status_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/validate-form-async", response_model=AsyncValidationResponse)
async def validate_form_async(
    application_type: Annotated[str, Form(..., description="Type of application service")],
    files: Optional[List[UploadFile]] = File(None, description="List of document files"),
    extraction_summary: Optional[str] = Form(None, description="JSON string of extraction summary"),
    current_user: UserModel = Depends(get_current_user_from_jwt)
) -> AsyncValidationResponse:
    """
    Submit a validation request for async processing.
    Returns immediately with a task ID that can be used to check status.
    
    This endpoint prevents blocking - other users can continue using the API
    while validation is processing in the background.
    """
    logger.info(f"Received async validation request for {application_type} from user {current_user.id}")
    
    # Validate inputs
    has_files = files is not None and len(files) > 0
    has_extraction = extraction_summary is not None
    
    if not has_files and not has_extraction:
        raise HTTPException(
            status_code=400,
            detail="Either 'files' or 'extraction_summary' must be provided"
        )
    
    # Get configuration
    config = get_verification_config(application_type)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"No verification configuration found for: {application_type}"
        )
    
    config_data = config.dict()
    user_id = current_user.id
    
    try:
        if has_extraction:
            # Mode 1: Validate pre-extracted data (lightweight, can be done quickly)
            logger.info("Mode: Async validation of pre-extracted data")
            
            try:
                extraction_data = json.loads(extraction_summary)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON in extraction_summary: {str(e)}"
                )
            
            # Submit validation task
            from app.celery_tasks import process_validation_task
            
            task = process_validation_task.delay(
                application_type=application_type,
                extraction_data=extraction_data,
                config_data=config_data,
                user_id=user_id
            )
            
            return AsyncValidationResponse(
                task_id=task.id,
                status="submitted",
                message=f"Validation task submitted. Use GET /validate-form-async/{task.id} to check status."
            )
        
        else:
            # Mode 2: Extract from files then validate (heavy processing)
            logger.info(f"Mode: Async extraction and validation from {len(files)} files")
            
            # Validate files first
            from app.utils.file_validator import file_validator
            file_validator.validate_files(files)
            
            # Save files to temporary location
            temp_files = []
            for file in files:
                # Create temporary file
                temp_fd, temp_path = tempfile.mkstemp(suffix=f"_{file.filename}")
                
                try:
                    content = await file.read()
                    
                    # Additional validation
                    file_validator.validate_file_content(content, file.filename)
                    
                    # Write to temp file
                    with os.fdopen(temp_fd, 'wb') as tmp_file:
                        tmp_file.write(content)
                    
                    temp_files.append(temp_path)
                except Exception as e:
                    # Clean up on error
                    try:
                        os.close(temp_fd)
                    except:
                        pass
                    for tf in temp_files:
                        try:
                            os.unlink(tf)
                        except:
                            pass
                    raise HTTPException(
                        status_code=400,
                        detail=f"Error processing file {file.filename}: {str(e)}"
                    )
            
            # Submit full validation task (extraction + validation)
            from app.celery_tasks import process_full_validation_task
            
            task = process_full_validation_task.delay(
                application_type=application_type,
                file_paths=temp_files,
                config_data=config_data,
                user_id=user_id
            )
            
            return AsyncValidationResponse(
                task_id=task.id,
                status="submitted",
                message=f"Validation task submitted. Use GET /validate-form-async/{task.id} to check status."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting async validation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit validation task: {str(e)}"
        )


@router.get("/validate-form-async/{task_id}", response_model=TaskStatusResponse)
async def get_validation_status(
    task_id: str,
    current_user: UserModel = Depends(get_current_user_from_jwt)
) -> TaskStatusResponse:
    """
    Check the status of an async validation task.
    
    Returns:
        - PENDING: Task is waiting to be processed
        - PROCESSING: Task is currently being processed
        - SUCCESS: Task completed successfully (result available)
        - FAILURE: Task failed (error message available)
    """
    from celery.result import AsyncResult
    from app.celery_config import celery_app
    
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == "PENDING":
        return TaskStatusResponse(
            task_id=task_id,
            status="pending",
            status_message="Task is waiting to be processed"
        )
    
    elif task_result.state == "PROCESSING":
        # Get progress info if available
        info = task_result.info or {}
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            progress=info.get("progress", 0),
            status_message=info.get("status", "Processing...")
        )
    
    elif task_result.state == "SUCCESS":
        result = task_result.result
        return TaskStatusResponse(
            task_id=task_id,
            status="completed",
            progress=100,
            status_message="Validation completed successfully",
            result=result
        )
    
    elif task_result.state == "FAILURE":
        error_info = str(task_result.info) if task_result.info else "Unknown error"
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            error=error_info,
            status_message="Task failed"
        )
    
    else:
        # Unknown state
        return TaskStatusResponse(
            task_id=task_id,
            status=task_result.state.lower(),
            status_message=f"Task is in state: {task_result.state}"
        )


@router.get("/validate-form-async/user/tasks")
async def get_user_tasks(
    current_user: UserModel = Depends(get_current_user_from_jwt),
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get recent validation tasks for the current user.
    
    Note: This is a simplified version. For production, you'd want to
    store task metadata in the database with user associations.
    """
    # This is a placeholder - in production you'd query the database
    # for tasks associated with the user
    return {
        "user_id": current_user.id,
        "message": "Task history not yet implemented. Use task_id from submission response to check status.",
        "note": "Store task IDs from AsyncValidationResponse to track your tasks"
    }
