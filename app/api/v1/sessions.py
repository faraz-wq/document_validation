from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import Session as SessionModel, User as UserModel
from app.api.v1.deps import get_current_user_from_jwt
import uuid
from pathlib import Path, PurePath
from typing import Dict, Any, List, Optional
from app.db.database import SessionLocal
from app.db.models import Session as SessionModel, Document, BoundingBox, Citation
from app.logging_config import get_logger

logger = get_logger(__name__)

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
    source_documents: Optional[List[dict]] = []
    errors: Optional[List[Any]] = []


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
            if bbox.field_name not in bounding_boxes:
                bounding_boxes[bbox.field_name] = []
            
            bounding_boxes[bbox.field_name].append({
                'filename': bbox.filename,
                'document_title': bbox.document_title,
                'page': bbox.page,
                'coordinates': bbox.coordinates
            })

    # Build citations
    citations = {}
    if session.citations:
        for citation in session.citations:
            citations[citation.field_name] = citation.citation

    # Extract source_documents and errors from summary_json
    summary_data = session.summary_json.copy() if session.summary_json else {}
    source_documents = summary_data.pop('source_documents', [])
    errors = summary_data.pop('_errors', [])

    # Return session data similar to existing /sessions/{session_id} endpoint
    return SessionDetailResponse(
        session_id=session.session_id,
        application_type=session.application_type,
        created_at=session.created_at,
        summary=summary_data,
        bounding_boxes=bounding_boxes,
        citations=citations,
        documents=document_list,
        source_documents=source_documents,
        errors=errors
    )
@router.get("/{session_id}/documents/{filename}")
def get_session_document(
    session_id: str,
    filename: str,
    current_user: UserModel = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Get a specific document from a session.
    Only allows access to documents from sessions owned by the user.
    """
    # Verify session ownership
    session = (
        db.query(SessionModel)
        .filter(SessionModel.session_id == session_id)
        .first()
    )

    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find document record to get the safe path
    doc_record = (
        db.query(Document)
        .filter(Document.session_id == session_id, Document.filename == filename)
        .first()
    )

    if not doc_record:
        raise HTTPException(status_code=404, detail="Document not found")

    # Path to document (data/documents_v1/...)
    documents_dir = Path("data/documents_v1")
    file_path = documents_dir / doc_record.file_path

    if not file_path.exists():
        logger.error(f"File not found on disk: {file_path}")
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=file_path,
        media_type=doc_record.mime_type or "application/pdf",
        filename=doc_record.filename
    )



def create_session(
    application_type: str,
    summary: Dict[str, Any],
    files: List[Dict[str, Any]],
    token_usage: Optional[Dict[str, int]] = None,
    user_id: Optional[int] = None,
    api_key_id: Optional[int] = None
) -> str:
    """Create a new session and store all related data"""
    session_id = str(uuid.uuid4())
    
    # Create directory for storing documents
    documents_dir = Path("data/documents_v1")
    documents_dir.mkdir(parents=True, exist_ok=True)

    # Create a new database session
    db = SessionLocal()
    try:
        # Extract bounding boxes and citations from summary
        # We need to be careful not to modify the original summary dict if it's used elsewhere
        # But here we are passed a copy or we should copy it
        summary_copy = summary.copy()
        bounding_boxes = summary_copy.pop('bounding_boxes', {})
        citations = summary_copy.pop('citations', {})
        token_usage_data = summary_copy.pop('_token_usage', token_usage)

        # Create session
        db_session = SessionModel(
            session_id=session_id,
            application_type=application_type,
            summary_json=summary_copy,
            token_usage_json=token_usage_data,
            user_id=user_id,
            api_key_id=api_key_id
        )
        db.add(db_session)

        # Insert documents
        for file_data in files:
            # Save document file to disk
            safe_filename = PurePath(file_data['filename']).name
            document_path = documents_dir / f"{session_id}_{safe_filename}"

            # Write the file content to disk
            with open(document_path, 'wb') as f:
                f.write(file_data['content'])

            # Store the relative file path in the database (relative to the documents directory)
            relative_path = str(document_path.relative_to(documents_dir))

            db_document = Document(
                session_id=session_id,
                filename=file_data['filename'],
                file_path=relative_path,  # Store the path to the file
                mime_type=file_data.get('mime_type'),
                file_size=len(file_data['content'])
            )
            db.add(db_document)

        # Insert bounding boxes
        for field_name, bbox_data in bounding_boxes.items():
            # Handle both list and single dict
            if isinstance(bbox_data, dict):
                bbox_list = [bbox_data]
            elif isinstance(bbox_data, list):
                bbox_list = bbox_data
            else:
                continue

            for bbox in bbox_list:
                if not isinstance(bbox, dict): continue
                
                db_bounding_box = BoundingBox(
                    session_id=session_id,
                    field_name=field_name,
                    filename=bbox.get('filename'),
                    document_title=bbox.get('document_title'),
                    page=bbox.get('page'),
                    coordinates=bbox.get('coordinates')
                )
                db.add(db_bounding_box)

        # Insert citations
        for field_name, citation in citations.items():
            db_citation = Citation(
                session_id=session_id,
                field_name=field_name,
                citation=citation
            )
            db.add(db_citation)

        db.commit()
        logger.info(f"Created session {session_id} for {application_type}")
        return session_id

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise
    finally:
        db.close()