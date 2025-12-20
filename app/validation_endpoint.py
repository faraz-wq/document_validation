"""
FastAPI endpoint for form-agnostic document validation.
POST /validate-form - Supports both raw files and extraction summaries
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from typing import List, Optional, Annotated
from app.validation_models import ValidationRequest, ValidationReport, ValidationIssue
from app.verification.engine import VerificationEngine
from app.verification.registry import get_verification_config
from app.services.extraction_service import get_extraction_service
from app.logging_config import get_logger
import json

logger = get_logger(__name__)

router = APIRouter()

# Initialize the NEW verification engine
verification_engine = VerificationEngine()


@router.post("/validate-form", response_model=ValidationReport)
async def validate_form(
    request: Request,
    application_type: Annotated[str, Form(..., description="Type of application service")],
    files: Optional[List[UploadFile]] = File(None, description="List of document files (optional if extraction_summary provided)"),
    extraction_summary: Optional[str] = Form(None, description="JSON string of extraction summary (optional if files provided)"),
    extraction_session_id: Optional[str] = Form(None, description="Original session ID if validating pre-extracted data")
) -> ValidationReport:
    """
    Validate a form submission - supports two modes and stores results in database.
    
    **Mode 1: Raw Files (Extract + Validate)**
    - Provide `application_type` and `files`
    - The endpoint will run OCR and VLM extraction, then validate
    
    **Mode 2: Pre-extracted Summary (Validate Only)**
    - Provide `application_type` and `extraction_summary` (as JSON string)
    - The endpoint will only validate the provided extraction
    
    Returns a validation report with a unique `validation_id` in metadata.
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

        # Get or create extraction summary
        if has_extraction:
            # Mode 2: Validate pre-extracted summary
            logger.info("Mode: Validate pre-extracted summary")
            try:
                extraction_data = json.loads(extraction_summary)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON in extraction_summary: {str(e)}"
                )
        else:
            # Mode 1: Extract from files then validate (AGNOSTIC EXTRACTION)
            logger.info(f"Mode: Extract from {len(files)} files guides by {application_type} rules")
            extraction_service = get_extraction_service()
            
            try:
                extraction_data = await extraction_service.extract_from_upload_files(
                    application_type=application_type,
                    files=files,
                    config=config,
                    combine_pdfs=True
                )
                _extraction_session_id = extraction_data.get('session_id')
                logger.info("Agnostic extraction completed successfully")
            except Exception as e:
                logger.error(f"Extraction failed: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=422,
                    detail=f"AI Extraction failed: {str(e)}"
                )
        
        # Validate using the NEW Engine
        logger.info("Starting NEW verification process")
        new_report = verification_engine.verify(extraction_data, config)
        
        # Map to legacy ValidationReport for frontend compatibility
        report_issues = []
        for i in new_report.issues:
            if not i.passed:
                report_issues.append(ValidationIssue(
                    field=i.field or "application",
                    severity=i.severity,
                    message=i.message,
                    requires_review=(i.severity == "error")
                ))

        report = ValidationReport(
            auto_approved=(new_report.overall_status == "verified"),
            confidence_score=1.0 if new_report.overall_status == "verified" else 0.7,
            issues=report_issues,
            summary=f"Audit Status: {new_report.overall_status}",
            metadata=new_report.metadata
        )
        
        # Save validation session to database
        try:
            import uuid
            from app.db.database import SessionLocal
            from app.db.models import ValidationSession
            
            validation_id = str(uuid.uuid4())
            
            # Get user/api_key from request
            user_id = None
            api_key_id = None
            if hasattr(request.state, 'user'):
                user_id = request.state.user.id
            if hasattr(request.state, 'api_key_id'):
                api_key_id = request.state.api_key_id
            
            db = SessionLocal()
            try:
                db_validation = ValidationSession(
                    validation_id=validation_id,
                    user_id=user_id,
                    api_key_id=api_key_id,
                    extraction_session_id=_extraction_session_id,
                    application_type=application_type,
                    validation_report_json=report.dict(),
                    extraction_summary_json=extraction_data,
                    auto_approved=report.auto_approved,
                    confidence_score=report.confidence_score,
                    error_count=report.metadata.get('error_count', 0),
                    warning_count=report.metadata.get('warning_count', 0),
                    info_count=report.metadata.get('info_count', 0)
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
        
        logger.info(
            f"Validation completed: "
            f"auto_approved={report.auto_approved}, "
            f"confidence={report.confidence_score:.2f}, "
            f"issues={len(report.issues)}"
        )
        
        return report
        
    except ValueError as e:
        # This happens when no validation rules are configured for the application type
        logger.error(f"Validation rules not found: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
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
    Validate a form submission using JSON request body (legacy endpoint).
    
    This endpoint only supports pre-extracted summaries.
    For raw file processing, use POST /validate-form with multipart/form-data.
    """
    logger.info(f"Received JSON validation request for application_type: {request.application_type}")
    
    if not request.extraction_summary:
        raise HTTPException(
            status_code=400,
            detail="extraction_summary is required for JSON endpoint. Use POST /validate-form with files for raw file processing."
        )
    
    try:
        # Run NEW validation
        config = get_verification_config(request.application_type)
        if not config:
            raise HTTPException(
                status_code=400,
                detail=f"No verification configuration found for: {request.application_type}"
            )
            
        new_report = verification_engine.verify(request.extraction_summary, config)
        
        # Map to legacy ValidationReport for frontend compatibility
        report_issues = []
        for i in new_report.issues:
            if not i.passed:
                report_issues.append(ValidationIssue(
                    field=i.field or "application",
                    severity=i.severity,
                    message=i.message,
                    requires_review=(i.severity == "error")
                ))

        report = ValidationReport(
            auto_approved=(new_report.overall_status == "verified"),
            confidence_score=1.0 if new_report.overall_status == "verified" else 0.7,
            issues=report_issues,
            summary=f"Audit Status: {new_report.overall_status}",
            metadata=new_report.metadata
        )
        
        logger.info(
            f"Validation completed for {request.application_type}: "
            f"auto_approved={report.auto_approved}, "
            f"confidence={report.confidence_score:.2f}, "
            f"issues={len(report.issues)}"
        )
        
        return report
        
    except ValueError as e:
        # This happens when no validation rules are configured for the application type
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
