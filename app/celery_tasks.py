"""
Celery tasks for background processing
Handles validation and extraction tasks asynchronously
"""

import os
import json
import tempfile
import mimetypes
from typing import Dict, Any, List
from celery import Task
from app.celery_config import celery_app
from app.logging_config import get_logger

logger = get_logger(__name__)


class CallbackTask(Task):
    """Base task with callbacks for progress tracking"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {task_id} failed: {exc}", exc_info=einfo)
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {task_id} completed successfully")


@celery_app.task(bind=True, base=CallbackTask, name="app.celery_tasks.process_validation_task")
def process_validation_task(
    self,
    application_type: str,
    extraction_data: Dict[str, Any],
    config_data: Dict[str, Any],
    user_id: int,
    api_key_id: int = None,
    extraction_session_id: str = None
) -> Dict[str, Any]:
    """
    Process validation task in background.
    
    Args:
        application_type: Type of application being validated
        extraction_data: Already extracted data to validate
        config_data: Verification configuration as dict
        user_id: User ID who initiated the task
        api_key_id: Optional API key ID
        extraction_session_id: Optional extraction session ID
    
    Returns:
        Dictionary with validation results
    """
    try:
        logger.info(f"Starting validation task {self.request.id} for {application_type}")
        
        # Import here to avoid circular dependencies
        from app.verification.engine import VerificationEngine
        from app.verification.schema import VerificationConfig
        from app.db.database import SessionLocal
        from app.db.models import ValidationSession
        import uuid
        
        # Update task state
        self.update_state(state="PROCESSING", meta={"progress": 10, "status": "Validating data"})
        
        # Reconstruct config from dict
        config = VerificationConfig(**config_data)
        
        # Perform validation
        verification_engine = VerificationEngine()
        report = verification_engine.verify(extraction_data, config)
        
        self.update_state(state="PROCESSING", meta={"progress": 70, "status": "Saving results"})
        
        # Save to database
        validation_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            err_c = report.validation_summary.errors
            warn_c = report.validation_summary.warnings
            
            db_validation = ValidationSession(
                validation_id=validation_id,
                user_id=user_id,
                api_key_id=api_key_id,
                extraction_session_id=extraction_session_id,
                application_type=application_type,
                validation_report_json=report.dict(),
                extraction_summary_json=extraction_data,
                auto_approved=(err_c == 0 and warn_c == 0),
                confidence_score=report.validation_summary.confidence_score,
                error_count=err_c,
                warning_count=warn_c,
                info_count=0
            )
            db.add(db_validation)
            db.commit()
            
            logger.info(f"Saved validation session: {validation_id}")
            
            # Add validation_id to report metadata
            report_dict = report.dict()
            report_dict['metadata']['validation_id'] = validation_id
            if extraction_session_id:
                report_dict['metadata']['extraction_session_id'] = extraction_session_id
            
            return {
                "status": "completed",
                "validation_id": validation_id,
                "report": report_dict
            }
            
        except Exception as db_error:
            db.rollback()
            logger.error(f"Database error in validation task: {db_error}", exc_info=True)
            raise
        finally:
            db.close()
    
    except Exception as exc:
        logger.error(f"Validation task failed: {exc}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 300))


@celery_app.task(bind=True, base=CallbackTask, name="app.celery_tasks.process_extraction_task")
def process_extraction_task(
    self,
    application_type: str,
    file_paths: List[str],
    config_data: Dict[str, Any],
    user_id: int,
    api_key_id: int = None,
    combine_pdfs: bool = True
) -> Dict[str, Any]:
    """
    Process extraction task in background.
    
    Args:
        application_type: Type of application
        file_paths: Paths to temporary files to process
        config_data: Verification configuration as dict
        user_id: User ID who initiated the task
        api_key_id: Optional API key ID
        combine_pdfs: Whether to combine PDF files
    
    Returns:
        Dictionary with extraction results
    """
    try:
        logger.info(f"Starting extraction task {self.request.id} for {application_type}")
        
        # Import here to avoid circular dependencies
        from app.verification.processor import VerificationProcessor
        from app.verification.schema import VerificationConfig
        from app.api.v1 import sessions as v1_sessions
        
        # Update task state
        self.update_state(state="PROCESSING", meta={"progress": 10, "status": "Loading files"})
        
        # Reconstruct config
        config = VerificationConfig(**config_data)
        
        # Load files from temporary paths
        file_data_list = []
        for file_path in file_paths:
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                filename = os.path.basename(file_path)
                mime_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
                
                file_data_list.append({
                    'filename': filename,
                    'content': content,
                    'mime_type': mime_type
                })
            except Exception as e:
                logger.error(f"Error loading file {file_path}: {e}")
                raise
        
        self.update_state(state="PROCESSING", meta={"progress": 30, "status": "Processing documents"})
        
        # Combine PDFs if requested
        if combine_pdfs and len(file_data_list) > 1:
            from app.utils.pdf_utils import combine_pdf_and_non_pdf_files
            file_data_list = combine_pdf_and_non_pdf_files(file_data_list)
        
        self.update_state(state="PROCESSING", meta={"progress": 40, "status": "Extracting data"})
        
        # Perform extraction
        processor = VerificationProcessor()
        result = processor.process(application_type, file_data_list, config)
        
        self.update_state(state="PROCESSING", meta={"progress": 80, "status": "Saving session"})
        
        # Save session to database
        try:
            session_id = v1_sessions.create_session(
                application_type=application_type,
                summary=result.copy(),
                files=file_data_list,
                user_id=user_id,
                api_key_id=api_key_id
            )
            result['session_id'] = session_id
            logger.info(f"Created extraction session: {session_id}")
        except Exception as db_error:
            logger.error(f"Failed to create extraction session: {db_error}", exc_info=True)
            # Continue even if database save fails
        
        # Clean up temporary files
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {file_path}: {e}")
        
        return {
            "status": "completed",
            "extraction_data": result
        }
    
    except Exception as exc:
        logger.error(f"Extraction task failed: {exc}", exc_info=True)
        
        # Clean up temporary files on error
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
            except:
                pass
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 300))


@celery_app.task(bind=True, base=CallbackTask, name="app.celery_tasks.process_full_validation_task")
def process_full_validation_task(
    self,
    application_type: str,
    file_paths: List[str],
    config_data: Dict[str, Any],
    user_id: int,
    api_key_id: int = None
) -> Dict[str, Any]:
    """
    Process full validation (extraction + validation) in background.
    
    This combines extraction and validation into a single task.
    
    Args:
        application_type: Type of application
        file_paths: Paths to temporary files to process
        config_data: Verification configuration as dict
        user_id: User ID who initiated the task
        api_key_id: Optional API key ID
    
    Returns:
        Dictionary with validation results
    """
    try:
        logger.info(f"Starting full validation task {self.request.id} for {application_type}")
        
        # Step 1: Extract data
        self.update_state(state="PROCESSING", meta={"progress": 10, "status": "Extracting data from files"})
        
        extraction_result = process_extraction_task(
            application_type=application_type,
            file_paths=file_paths,
            config_data=config_data,
            user_id=user_id,
            api_key_id=api_key_id,
            combine_pdfs=True
        )
        
        extraction_data = extraction_result["extraction_data"]
        extraction_session_id = extraction_data.get("session_id")
        
        # Step 2: Validate extracted data
        self.update_state(state="PROCESSING", meta={"progress": 60, "status": "Validating extracted data"})
        
        validation_result = process_validation_task(
            application_type=application_type,
            extraction_data=extraction_data,
            config_data=config_data,
            user_id=user_id,
            api_key_id=api_key_id,
            extraction_session_id=extraction_session_id
        )
        
        return validation_result
    
    except Exception as exc:
        logger.error(f"Full validation task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=min(2 ** self.request.retries, 300))
