import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.models import Session as SessionModel, Document, BoundingBox, Citation
from app.db.database import get_db, SessionLocal
from app.logging_config import get_logger

logger = get_logger(__name__)

class SessionDatabase:
    def __init__(self):
        # Create directory for storing documents at the project root level
        self.documents_dir = Path("data/documents_v1")
        self.documents_dir.mkdir(parents=True, exist_ok=True)

    def init_database(self):
        """Initialize the database schema - this is now handled by SQLAlchemy migrations"""
        # Database initialization is now done via SQLAlchemy models and migration scripts
        logger.info("Database initialization handled via SQLAlchemy models")
    
    def create_session(
        self,
        application_type: str,
        summary: Dict[str, Any],
        files: List[Dict[str, Any]],
        token_usage: Optional[Dict[str, int]] = None,
        *,
        user_id: int | None = None,
        api_key_id: int | None = None
    ) -> str:
        """Create a new session and store all related data"""
        session_id = str(uuid.uuid4())

        # Create a new database session
        db = SessionLocal()
        try:
            # Extract bounding boxes and citations from summary
            bounding_boxes = summary.pop('bounding_boxes', {})
            citations = summary.pop('citations', {})
            token_usage_data = summary.pop('_token_usage', token_usage)

            # Create session
            db_session = SessionModel(
                session_id=session_id,
                application_type=application_type,
                summary_json=summary,
                token_usage_json=token_usage_data,
                user_id=user_id,
                api_key_id=api_key_id
            )
            db.add(db_session)

            # Insert documents
            for file_data in files:
                # Save document file to disk
                from pathlib import PurePath
                safe_filename = PurePath(file_data['filename']).name
                document_path = self.documents_dir / f"{session_id}_{safe_filename}"

                # Write the file content to disk
                with open(document_path, 'wb') as f:
                    f.write(file_data['content'])

                # Store the relative file path in the database (relative to the documents directory)
                relative_path = str(document_path.relative_to(self.documents_dir))

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
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a complete session with all related data"""
        db = SessionLocal()
        try:
            # Get session
            db_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            if not db_session:
                return None

            # Get related data
            db_documents = db.query(Document).filter(Document.session_id == session_id).all()
            db_bounding_boxes = db.query(BoundingBox).filter(BoundingBox.session_id == session_id).all()
            db_citations = db.query(Citation).filter(Citation.session_id == session_id).all()

            documents = []
            for doc in db_documents:
                documents.append({
                    'filename': doc.filename,
                    'file_path': doc.file_path,
                    'mime_type': doc.mime_type
                })

            bounding_boxes = {}
            for bbox in db_bounding_boxes:
                if bbox.field_name not in bounding_boxes:
                    bounding_boxes[bbox.field_name] = []
                
                bounding_boxes[bbox.field_name].append({
                    'filename': bbox.filename,
                    'page': bbox.page,
                    'coordinates': bbox.coordinates
                })

            citations = {}
            for citation in db_citations:
                citations[citation.field_name] = citation.citation

            # Reconstruct full response
            result = {
                'session_id': session_id,
                'application_type': db_session.application_type,
                'created_at': db_session.created_at.isoformat() if db_session.created_at else None,
                'summary': db_session.summary_json,
                'bounding_boxes': bounding_boxes,
                'citations': citations,
                'documents': documents
            }

            if db_session.token_usage_json:
                result['_token_usage'] = db_session.token_usage_json

            logger.info(f"Retrieved session {session_id}")
            return result

        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}", exc_info=True)
            return None
        finally:
            db.close()

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions"""
        db = SessionLocal()
        try:
            db_sessions = db.query(SessionModel).order_by(SessionModel.created_at.desc()).limit(limit).all()

            sessions = []
            for db_session in db_sessions:
                sessions.append({
                    'session_id': db_session.session_id,
                    'application_type': db_session.application_type,
                    'created_at': db_session.created_at.isoformat() if db_session.created_at else None
                })

            return sessions

        finally:
            db.close()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data"""
        db = SessionLocal()
        try:
            # Get documents to delete their files
            db_documents = db.query(Document).filter(Document.session_id == session_id).all()

            # Delete the actual document files
            for db_doc in db_documents:
                full_path = self.documents_dir / db_doc.file_path
                if full_path.exists():
                    try:
                        full_path.unlink()  # Delete the file
                        logger.info(f"Deleted document file: {full_path}")
                    except Exception as file_error:
                        logger.error(f"Error deleting document file {full_path}: {file_error}")

            # Delete from database (CASCADE should handle related records)
            db_session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            if db_session:
                db.delete(db_session)
                db.commit()
                logger.info(f"Deleted session {session_id}")
                return True
            else:
                logger.warning(f"Session {session_id} not found for deletion")
                return False

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
            return False
        finally:
            db.close()

# Global database instance
db = SessionDatabase()
