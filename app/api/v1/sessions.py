from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import Session as SessionModel, User as UserModel
from app.api.v1.deps import get_current_user_from_jwt

router = APIRouter(prefix="/me/sessions", tags=["v1-user-sessions"])

# Response models
class UserSessionItem(BaseModel):
    session_id: str
    application_type: str
    created_at: datetime
    file_count: int


class UserSessionListResponse(BaseModel):
    items: List[UserSessionItem]
    total_count: int


@router.get("/", response_model=UserSessionListResponse)
def list_user_sessions(
    current_user: UserModel = Depends(get_current_user_from_jwt),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get list of sessions owned by the current user.

    Returns a paginated list of sessions owned by the authenticated user.
    Requires a valid JWT token in the Authorization header.

    Args:
        limit: Number of sessions to return per page. Must be between 1 and 100. Defaults to 50.
        offset: Number of sessions to skip before starting to collect the result set. Defaults to 0.
        current_user: The authenticated user (automatically extracted from JWT token)
        db: Database session dependency

    Returns:
        UserSessionListResponse: A response containing a list of user sessions and the total count

    Raises:
        HTTPException: 401 if the JWT token is invalid or missing
        HTTPException: 422 if query parameters are invalid (e.g., limit < 1 or > 100)
    """
    # Count total sessions for user
    total_count = db.query(SessionModel).filter(SessionModel.user_id == current_user.id).count()

    # Get sessions with pagination
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == current_user.id)
        .order_by(SessionModel.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Calculate file count for each session (this might require joining with Document model)
    items = []
    for session in sessions:
        # Count documents for each session
        file_count = len(session.documents) if hasattr(session, 'documents') else 0
        items.append(
            UserSessionItem(
                session_id=session.session_id,
                application_type=session.application_type,
                created_at=session.created_at,
                file_count=file_count
            )
        )

    return UserSessionListResponse(items=items, total_count=total_count)


# Response model for session details
class SessionDetailResponse(BaseModel):
    session_id: str
    application_type: str
    created_at: datetime
    summary: dict
    bounding_boxes: dict = {}
    citations: dict = {}
    documents: list = []


@router.get("/{session_id}", response_model=SessionDetailResponse)
def get_user_session(
    session_id: str,
    current_user: UserModel = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Get a specific session owned by the current user.

    Retrieves detailed information about a specific session owned by the authenticated user.
    Only returns sessions that belong to the authenticated user. If the session doesn't
    exist or doesn't belong to the user, returns a 404 error.

    Args:
        session_id: Unique identifier of the session to retrieve
        current_user: The authenticated user (automatically extracted from JWT token)
        db: Database session dependency

    Returns:
        SessionDetailResponse: Detailed information about the session including
                              summary, bounding boxes, citations, and documents

    Raises:
        HTTPException: 401 if the JWT token is invalid or missing
        HTTPException: 404 if the session doesn't exist or doesn't belong to the user
    """
    # Fetch session with relationships
    session = (
        db.query(SessionModel)
        .filter(SessionModel.session_id == session_id)
        .first()
    )

    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build document list
    document_list = []
    if session.documents:
        for doc in session.documents:
            document_list.append({
                'filename': doc.filename,
                'file_path': doc.file_path,
                'mime_type': doc.mime_type
            })

    # Build bounding boxes
    bounding_boxes = {}
    if session.bounding_boxes:
        for bbox in session.bounding_boxes:
            bounding_boxes[bbox.field_name] = {
                'filename': bbox.filename,
                'page': bbox.page,
                'coordinates': bbox.coordinates
            }

    # Build citations
    citations = {}
    if session.citations:
        for citation in session.citations:
            citations[citation.field_name] = citation.citation

    # Return session data similar to existing /sessions/{session_id} endpoint
    return SessionDetailResponse(
        session_id=session.session_id,
        application_type=session.application_type,
        created_at=session.created_at,
        summary=session.summary_json,
        bounding_boxes=bounding_boxes,
        citations=citations,
        documents=document_list
    )