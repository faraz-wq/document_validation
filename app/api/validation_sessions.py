"""
API endpoints for managing and viewing validation sessions.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.db.database import SessionLocal
from app.db.models import ValidationSession
from app.logging_config import get_logger
from sqlalchemy.orm import Session

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/validation-sessions")
async def list_validation_sessions(
    limit: int = 50,
    offset: int = 0,
    application_type: Optional[str] = None,
    auto_approved: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    List validation sessions with optional filtering.
    
    Query Parameters:
    - limit: Maximum number of sessions to return (default: 50)
    - offset: Number of sessions to skip (default: 0)
    - application_type: Filter by application type
    - auto_approved: Filter by auto-approval status (true/false)
    
    Returns:
        List of validation sessions with summary information
    """
    try:
        query = db.query(ValidationSession)
        
        # Apply filters
        if application_type:
            query = query.filter(ValidationSession.application_type == application_type)
        if auto_approved is not None:
            query = query.filter(ValidationSession.auto_approved == auto_approved)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        sessions = query.order_by(ValidationSession.created_at.desc()).offset(offset).limit(limit).all()
        
        # Format response
        items = []
        for session in sessions:
            items.append({
                "validation_id": session.validation_id,
                "application_type": session.application_type,
                "auto_approved": session.auto_approved,
                "confidence_score": session.confidence_score,
                "error_count": session.error_count,
                "warning_count": session.warning_count,
                "info_count": session.info_count,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "extraction_session_id": session.extraction_session_id
            })
        
        return {
            "items": items,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Error listing validation sessions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list validation sessions: {str(e)}")


@router.get("/validation-sessions/{validation_id}")
async def get_validation_session(
    validation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific validation session.
    
    Path Parameters:
    - validation_id: UUID of the validation session
    
    Returns:
        Complete validation session details including:
        - Validation report (issues, confidence, approval status)
        - Extraction summary (the data that was validated)
        - Metadata (timestamps, user info, etc.)
    """
    try:
        session = db.query(ValidationSession).filter(
            ValidationSession.validation_id == validation_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Validation session {validation_id} not found")
        
        return {
            "validation_id": session.validation_id,
            "application_type": session.application_type,
            "auto_approved": session.auto_approved,
            "confidence_score": session.confidence_score,
            "error_count": session.error_count,
            "warning_count": session.warning_count,
            "info_count": session.info_count,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "extraction_session_id": session.extraction_session_id,
            "validation_report": session.validation_report_json,
            "extraction_summary": session.extraction_summary_json,
            "user_id": session.user_id,
            "api_key_id": session.api_key_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving validation session {validation_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve validation session: {str(e)}")


@router.delete("/validation-sessions/{validation_id}")
async def delete_validation_session(
    validation_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a validation session.
    
    Path Parameters:
    - validation_id: UUID of the validation session to delete
    
    Returns:
        Success message
    """
    try:
        session = db.query(ValidationSession).filter(
            ValidationSession.validation_id == validation_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail=f"Validation session {validation_id} not found")
        
        db.delete(session)
        db.commit()
        
        logger.info(f"Deleted validation session: {validation_id}")
        
        return {"message": f"Validation session {validation_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting validation session {validation_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete validation session: {str(e)}")


@router.get("/validation-sessions/stats/summary")
async def get_validation_stats(db: Session = Depends(get_db)):
    """
    Get summary statistics for all validation sessions.
    
    Returns:
        Statistics including:
        - Total sessions
        - Auto-approved count
        - Average confidence score
        - Breakdown by application type
    """
    try:
        total_sessions = db.query(ValidationSession).count()
        auto_approved_count = db.query(ValidationSession).filter(
            ValidationSession.auto_approved == True
        ).count()
        
        # Calculate average confidence score
        from sqlalchemy import func
        avg_confidence = db.query(func.avg(ValidationSession.confidence_score)).scalar() or 0.0
        
        # Get breakdown by application type
        type_breakdown = db.query(
            ValidationSession.application_type,
            func.count(ValidationSession.validation_id).label('count')
        ).group_by(ValidationSession.application_type).all()
        
        return {
            "total_sessions": total_sessions,
            "auto_approved_count": auto_approved_count,
            "auto_approved_percentage": (auto_approved_count / total_sessions * 100) if total_sessions > 0 else 0,
            "average_confidence_score": float(avg_confidence),
            "type_breakdown": [
                {"application_type": type_name, "count": count}
                for type_name, count in type_breakdown
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting validation stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get validation stats: {str(e)}")
