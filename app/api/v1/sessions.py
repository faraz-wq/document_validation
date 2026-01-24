from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.db.database import get_db, SessionLocal
from app.db.models import Session as SessionModel, User as UserModel, Document, BoundingBox, Citation
from app.api.v1.deps import get_current_user_from_jwt
from pathlib import Path, PurePath
import uuid
from app.logging_config import get_logger
from app.utils.gcs_storage import get_gcs_storage, is_gcs_enabled
from google.cloud.exceptions import NotFound
import io

logger = get_logger(__name__)

router = APIRouter(prefix="/me/sessions", tags=["v1-user-sessions"])

# Response model for session list item
class SessionListItem(BaseModel):
    session_id: str
    application_type: str
    created_at: datetime
    file_count: int
    session_type: str  # 'extraction' or 'validation'
    confidence_score: Optional[float] = None
    error_count: Optional[int] = None
    warning_count: Optional[int] = None

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


@router.get("", response_model=Dict[str, Any])
def list_user_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    List all sessions (extraction and validation) owned by the current user.

    Returns a paginated list of sessions with summary information.
    Sessions are ordered by creation date (newest first).

    Args:
        limit: Maximum number of sessions to return (1-100, default: 50)
        offset: Number of sessions to skip for pagination (default: 0)
        current_user: The authenticated user (automatically extracted from JWT token)
        db: Database session dependency

    Returns:
        Dict containing:
        - items: List of session summaries
        - total_count: Total number of sessions for this user
        - limit: The limit used
        - offset: The offset used

    Raises:
        HTTPException: 401 if the JWT token is invalid or missing
    """
    from app.db.models import ValidationSession
    
    # Get validation sessions
    validation_sessions_query = (
        db.query(ValidationSession)
        .filter(ValidationSession.user_id == current_user.id)
    )
    
    # Get extraction sessions
    extraction_sessions_query = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == current_user.id)
    )
    
    # Fetch all validation sessions first
    validation_sessions = validation_sessions_query.all()
    
    # Collect extraction IDs associated with validation sessions
    linked_extraction_ids = {
        vs.extraction_session_id 
        for vs in validation_sessions 
        if vs.extraction_session_id
    }
    
    # Get extraction sessions query
    extraction_sessions_query = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == current_user.id)
    )
    
    # Filter out extractions that have been validated
    if linked_extraction_ids:
        extraction_sessions_query = extraction_sessions_query.filter(
            SessionModel.session_id.notin_(list(linked_extraction_ids))
        )
    
    # Fetch extraction sessions
    extraction_sessions = extraction_sessions_query.all()
    
    # Calculate totals
    total_validation = len(validation_sessions)
    total_extraction = len(extraction_sessions)
    total_count = total_validation + total_extraction
    
    # Convert to list items
    items = []
    
    for session in validation_sessions:
        items.append({
            'session_id': session.validation_id,
            'application_type': session.application_type,
            'created_at': session.created_at,
            'file_count': 0,  # We don't track this directly for validation sessions
            'session_type': 'validation',
            'confidence_score': session.confidence_score,
            'error_count': session.error_count,
            'warning_count': session.warning_count
        })
    
    for session in extraction_sessions:
        # Count documents
        doc_count = db.query(Document).filter(Document.session_id == session.session_id).count()
        
        items.append({
            'session_id': session.session_id,
            'application_type': session.application_type,
            'created_at': session.created_at,
            'file_count': doc_count,
            'session_type': 'extraction',
            'confidence_score': None,
            'error_count': None,
            'warning_count': None
        })
    
    # Sort by created_at descending
    items.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Apply pagination
    paginated_items = items[offset:offset + limit]
    
    return {
        'items': paginated_items,
        'total_count': total_count,
        'limit': limit,
        'offset': offset
    }


@router.get("/{session_id}", response_model=SessionDetailResponse)

def get_user_session(
    session_id: str,
    current_user: UserModel = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Get a specific session owned by the current user.

    Retrieves detailed information about a specific session owned by the authenticated user.
    Supports both regular extraction sessions and validation sessions.
    Only returns sessions that belong to the authenticated user. If the session doesn't
    exist or doesn't belong to the user, returns a 404 error.

    Args:
        session_id: Unique identifier of the session to retrieve (can be extraction or validation session ID)
        current_user: The authenticated user (automatically extracted from JWT token)
        db: Database session dependency

    Returns:
        SessionDetailResponse: Detailed information about the session including
                              summary, bounding boxes, citations, and documents

    Raises:
        HTTPException: 401 if the JWT token is invalid or missing
        HTTPException: 404 if the session doesn't exist or doesn't belong to the user
    """
    # First check if this is a validation session
    from app.db.models import ValidationSession
    
    validation_session = (
        db.query(ValidationSession)
        .filter(ValidationSession.validation_id == session_id)
        .first()
    )
    
    if validation_session:
        # Verify ownership (allow None user_id for legacy sessions)
        if validation_session.user_id is not None and validation_session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # For validation sessions, return the validation report data
        report_data = validation_session.validation_report_json or {}
        extraction_data = validation_session.extraction_summary_json or {}
        
        # Get documents from the linked extraction session if available
        document_list = []
        bounding_boxes = {}
        citations = {}
        
        if validation_session.extraction_session_id:
            extraction_session = (
                db.query(SessionModel)
                .filter(SessionModel.session_id == validation_session.extraction_session_id)
                .first()
            )
            
            if extraction_session:
                # Build document list from extraction session
                if extraction_session.documents:
                    for doc in extraction_session.documents:
                        document_list.append({
                            'filename': doc.filename,
                            'file_path': doc.file_path,
                            'mime_type': doc.mime_type
                        })
                
                # Build bounding boxes from extraction session
                if extraction_session.bounding_boxes:
                    for bbox in extraction_session.bounding_boxes:
                        if bbox.field_name not in bounding_boxes:
                            bounding_boxes[bbox.field_name] = []
                        
                        bounding_boxes[bbox.field_name].append({
                            'filename': bbox.filename,
                            'document_title': bbox.document_title,
                            'page': bbox.page,
                            'coordinates': bbox.coordinates
                        })
                
                # Build citations from extraction session
                if extraction_session.citations:
                    for citation in extraction_session.citations:
                        citations[citation.field_name] = citation.citation
        
        # Extract summary from validation report
        summary_data = report_data.get('summary', extraction_data.get('summary', {}))
        source_documents = extraction_data.get('source_documents', [])
        
        # Get errors from validation report
        issues = report_data.get('issues', [])
        errors = [issue for issue in issues if issue.get('severity') == 'error']
        
        return SessionDetailResponse(
            session_id=session_id,
            application_type=validation_session.application_type,
            created_at=validation_session.created_at,
            summary=summary_data,
            bounding_boxes=bounding_boxes,
            citations=citations,
            documents=document_list,
            source_documents=source_documents,
            errors=errors
        )
    
    # Otherwise, fetch as a regular extraction session
    session = (
        db.query(SessionModel)
        .filter(SessionModel.session_id == session_id)
        .first()
    )

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify ownership (allow None user_id for legacy sessions)
    if session.user_id is not None and session.user_id != current_user.id:
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
    Checks both the session itself and any linked extraction session.
    Supports both GCS and local file storage.
    """
    # First check if this is a validation session
    from app.db.models import ValidationSession
    
    validation_session = (
        db.query(ValidationSession)
        .filter(ValidationSession.validation_id == session_id)
        .first()
    )
    
    # Determine which session(s) to check for documents
    session_ids_to_check = [session_id]
    
    if validation_session:
        # Verify ownership via validation session (allow None user_id for legacy sessions)
        if validation_session.user_id is not None and validation_session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # If there's a linked extraction session, check it too
        if validation_session.extraction_session_id:
            session_ids_to_check.append(validation_session.extraction_session_id)
    else:
        # Check if it's a regular session
        session = (
            db.query(SessionModel)
            .filter(SessionModel.session_id == session_id)
            .first()
        )
        
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify ownership (allow None user_id for legacy sessions)
        if session.user_id is not None and session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")

    # Find document record in any of the relevant sessions
    doc_record = None
    for sid in session_ids_to_check:
        doc_record = (
            db.query(Document)
            .filter(Document.session_id == sid, Document.filename == filename)
            .first()
        )
        if doc_record:
            break

    if not doc_record:
        logger.error(f"Document not found: {filename} in sessions {session_ids_to_check}")
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if using GCS storage
    if is_gcs_enabled():
        try:
            gcs = get_gcs_storage()
            
            # Download document from GCS
            file_content = gcs.download_document(doc_record.file_path)
            
            # Return as streaming response
            return StreamingResponse(
                io.BytesIO(file_content),
                media_type=doc_record.mime_type or "application/pdf",
                headers={
                    "Content-Disposition": f'inline; filename="{doc_record.filename}"'
                }
            )
            
        except NotFound:
            logger.error(f"File not found in GCS: {doc_record.file_path}")
            raise HTTPException(status_code=404, detail="File not found in cloud storage")
        except Exception as e:
            logger.error(f"Error retrieving file from GCS: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error retrieving file from cloud storage")
    else:
        # Legacy: Local file storage
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

        # Check if GCS is enabled
        use_gcs = is_gcs_enabled()
        
        if use_gcs:
            logger.info(f"Using GCS storage for session {session_id}")
            gcs = get_gcs_storage()
        else:
            logger.info(f"Using local storage for session {session_id}")
            # Create directory for storing documents locally
            documents_dir = Path("data/documents_v1")
            documents_dir.mkdir(parents=True, exist_ok=True)

        # Insert documents
        for file_data in files:
            safe_filename = PurePath(file_data['filename']).name
            
            if use_gcs:
                # Upload to GCS
                try:
                    gcs_path = gcs.upload_document(
                        file_content=file_data['content'],
                        session_id=session_id,
                        filename=safe_filename,
                        mime_type=file_data.get('mime_type')
                    )
                    file_path = gcs_path  # Store GCS path in database
                    
                except Exception as e:
                    logger.error(f"Failed to upload to GCS: {e}", exc_info=True)
                    raise Exception(f"Failed to upload document to cloud storage: {str(e)}")
            else:
                # Save to local disk
                document_path = documents_dir / f"{session_id}_{safe_filename}"
                
                with open(document_path, 'wb') as f:
                    f.write(file_data['content'])
                
                # Store the relative file path in the database
                file_path = str(document_path.relative_to(documents_dir))

            # Create document record
            db_document = Document(
                session_id=session_id,
                filename=file_data['filename'],
                file_path=file_path,  # GCS path or local relative path
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
        
        storage_type = "GCS" if use_gcs else "local"
        logger.info(f"Created session {session_id} for {application_type} using {storage_type} storage")
        return session_id

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise
    finally:
        db.close()