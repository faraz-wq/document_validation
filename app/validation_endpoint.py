"""
FastAPI endpoint for form-agnostic document validation.
POST /validate-form - Supports both raw files and extraction summaries
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, Depends
from typing import List, Optional, Annotated, Dict, Any
from app.validation_models import ValidationRequest, ValidationReport, ValidationIssue
from app.verification.engine import VerificationEngine
from app.verification.registry import get_verification_config
from app.services.extraction_service import get_extraction_service
from app.logging_config import get_logger
from app.api.v1.deps import get_current_user_from_jwt
from app.db.models import User as UserModel
import json

logger = get_logger(__name__)

router = APIRouter()

# Initialize the NEW verification engine
verification_engine = VerificationEngine()

def _flatten_citations(citations: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Helper to flatten nested citations for frontend compatibility."""
    items = []
    for k, v in citations.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_citations(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


@router.post("/validate-form", response_model=ValidationReport)
async def validate_form(
    request: Request,
    application_type: Annotated[str, Form(..., description="Type of application service")],
    files: Optional[List[UploadFile]] = File(None, description="List of document files (optional if extraction_summary provided)"),
    extraction_summary: Optional[str] = Form(None, description="JSON string of extraction summary (optional if files provided)"),
    extraction_session_id: Optional[str] = Form(None, description="Original session ID if validating pre-extracted data"),
    current_user: UserModel = Depends(get_current_user_from_jwt)
) -> ValidationReport:
    """
    Validate a form submission - uses Universal Extraction Workflow.
    Returns: Canonical Universal Extraction Response (Schema-Last).
    
    Now runs heavy processing in a thread pool to prevent blocking other requests.
    """
    logger.info(f"Received validation request for application_type: {application_type}")
    
    try:
        # Determine which mode we're in
        has_files = files is not None and len(files) > 0
        has_extraction = extraction_summary is not None
        
        if not has_files and not has_extraction:
            raise HTTPException(
                status_code=400,
                detail="Either 'files' or 'extraction_summary' must be provided"
            )
        
        if has_files and has_extraction:
            logger.warning("Both files and extraction_summary provided, using extraction_summary")
        
        _extraction_session_id = extraction_session_id
        
        # 0. Get Configuration (Guided AI Extraction & Verification)
        config = get_verification_config(application_type)
        if not config:
            raise HTTPException(
                status_code=400,
                detail=f"No verification configuration found for: {application_type}"
            )

        
        # Get user/api_key from dependency
        user_id = current_user.id
        api_key_id = None # API Key not yet supported via multipart-form
        
        # Get or create extraction summary
        if has_extraction:
            # Mode 2: Validate pre-extracted summary (lightweight)
            logger.info("Mode: Validate pre-extracted summary")
            try:
                extraction_data = json.loads(extraction_summary)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON in extraction_summary: {str(e)}"
                )
            
            # Run validation in thread pool to prevent blocking
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            loop = asyncio.get_event_loop()
            
            def run_validation():
                """Run validation in a separate thread"""
                return verification_engine.verify(extraction_data, config)
            
            # Execute in thread pool
            with ThreadPoolExecutor(max_workers=1) as executor:
                report = await loop.run_in_executor(executor, run_validation)
        else:
            # Mode 1: Extract from files then validate (HEAVY PROCESSING)
            logger.info(f"Mode: Extract from {len(files)} files guided by {application_type} rules")
            
            # Run extraction and validation in thread pool to prevent blocking
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            loop = asyncio.get_event_loop()
            
            def run_extraction_and_validation():
                """Run extraction and validation in a separate thread"""
                # Import here to avoid issues with async context
                from app.services.extraction_service import get_extraction_service
                import asyncio
                
                # Create a new event loop for this thread
                thread_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(thread_loop)
                
                try:
                    extraction_service = get_extraction_service()
                    
                    # Run the async extraction in this thread's event loop
                    extraction_data = thread_loop.run_until_complete(
                        extraction_service.extract_from_upload_files(
                            application_type=application_type,
                            files=files,
                            config=config,
                            combine_pdfs=True,
                            user_id=user_id,
                            api_key_id=api_key_id
                        )
                    )
                    
                    session_id = extraction_data.get('session_id')
                    logger.info(f"Agnostic extraction completed successfully, session: {session_id}")
                    
                    # Run validation
                    report = verification_engine.verify(extraction_data, config)
                    
                    return report, extraction_data, session_id
                finally:
                    thread_loop.close()
            
            # Execute in thread pool (this prevents blocking the main event loop)
            with ThreadPoolExecutor(max_workers=1) as executor:
                report, extraction_data, _extraction_session_id = await loop.run_in_executor(
                    executor, 
                    run_extraction_and_validation
                )
        
        # Save validation session to database (quick operation, can stay in main thread)
        try:
            import uuid
            from app.db.database import SessionLocal
            from app.db.models import ValidationSession
            
            validation_id = str(uuid.uuid4())
            
            db = SessionLocal()
            try:
                # Calculate counts from strict schema
                err_c = report.validation_summary.errors
                warn_c = report.validation_summary.warnings
                
                db_validation = ValidationSession(
                    validation_id=validation_id,
                    user_id=user_id,
                    api_key_id=api_key_id,
                    extraction_session_id=_extraction_session_id,
                    application_type=application_type,
                    validation_report_json=report.dict(),
                    extraction_summary_json=extraction_data if has_extraction else {},
                    auto_approved=(err_c == 0 and warn_c == 0),
                    confidence_score=report.validation_summary.confidence_score,
                    error_count=err_c,
                    warning_count=warn_c,
                    info_count=0
                )
                db.add(db_validation)
                db.commit()
                logger.info(f"Saved validation session: {validation_id}")
                
                # Add validation_id to metadata
                report.metadata['validation_id'] = validation_id
                if _extraction_session_id:
                    report.metadata['extraction_session_id'] = _extraction_session_id

                
            except Exception as db_error:
                db.rollback()
                logger.error(f"Failed to save validation session: {db_error}", exc_info=True)
                # Continue even if database save fails
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in validation session storage: {str(e)}", exc_info=True)
            # Continue even if storage fails
        
        # Log summary
        summ = report.validation_summary
        logger.info(
            f"Validation completed: "
            f"confidence={summ.confidence_score:.2f}, "
            f"errors={summ.errors}, warnings={summ.warnings}"
        )
        
        return report
        
    except ValueError as e:
        logger.error(f"Validation rules not found: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during validation: {str(e)}"
        )


@router.post("/validate-form-json", response_model=ValidationReport)
async def validate_form_json(request: ValidationRequest) -> ValidationReport:
    """
    Validate a form submission using JSON request body.
    Returns: Canonical Universal Extraction Response (Schema-Last).
    """
    logger.info(f"Received JSON validation request for application_type: {request.application_type}")
    
    if not request.extraction_summary:
        raise HTTPException(
            status_code=400,
            detail="extraction_summary is required."
        )
    
    try:
        config = get_verification_config(request.application_type)
        if not config:
            raise HTTPException(
                status_code=400,
                detail=f"No verification configuration found for: {request.application_type}"
            )
            
        report = verification_engine.verify(request.extraction_summary, config)
        
        summ = report.validation_summary
        logger.info(
            f"Validation completed for {request.application_type}: "
            f"confidence={summ.confidence_score:.2f}, "
            f"errors={summ.errors}"
        )
        
        return report
        
    except ValueError as e:
        logger.error(f"Validation rules not found: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during validation: {str(e)}"
        )


@router.get("/validate-form/rules/{application_type}")
async def get_validation_rules(application_type: str):
    """
    Get the validation rules configured for a specific application type.
    Useful for debugging and understanding what validations will be performed.
    
    Returns:
        Dictionary with rule configuration including required fields, documents, etc.
    """
    config = get_verification_config(application_type)
    
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"No verification configuration found for: {application_type}"
        )
    
    return {
        "application_type": config.application_type,
        "key_details": [d.dict() for d in config.key_details],
        "rules": [r.dict() for r in config.rules]
    }


@router.get("/validate-form/supported-types")
async def list_supported_types():
    """
    List all application types that have validation rules configured.
    
    Returns:
        List of supported application type names
    """
    from app.verification.registry import VERIFICATION_REGISTRY
    
    return {
        "supported_types": list(VERIFICATION_REGISTRY.keys()),
        "count": len(VERIFICATION_REGISTRY)
    }
