import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from app.logging_config import get_logger

logger = get_logger(__name__)

class SessionDatabase:
    def __init__(self, db_path: str = "data/sessions.db"):
        # Ensure data directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                application_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary_json TEXT NOT NULL,
                token_usage_json TEXT
            )
        """)
        
        # Documents table (stores uploaded files)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_data BLOB NOT NULL,
                mime_type TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Bounding boxes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bounding_boxes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                page INTEGER NOT NULL,
                coordinates TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        # Citations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                citation TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def create_session(
        self,
        application_type: str,
        summary: Dict[str, Any],
        files: List[Dict[str, Any]],
        token_usage: Optional[Dict[str, int]] = None
    ) -> str:
        """Create a new session and store all related data"""
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extract bounding boxes and citations from summary
            bounding_boxes = summary.pop('bounding_boxes', {})
            citations = summary.pop('citations', {})
            token_usage_data = summary.pop('_token_usage', token_usage)
            
            # Insert session
            cursor.execute("""
                INSERT INTO sessions (session_id, application_type, summary_json, token_usage_json)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                application_type,
                json.dumps(summary),
                json.dumps(token_usage_data) if token_usage_data else None
            ))
            
            # Insert documents
            for file_data in files:
                cursor.execute("""
                    INSERT INTO documents (session_id, filename, file_data, mime_type)
                    VALUES (?, ?, ?, ?)
                """, (
                    session_id,
                    file_data['filename'],
                    file_data['content'],
                    file_data.get('mime_type')
                ))
            
            # Insert bounding boxes
            for field_name, bbox in bounding_boxes.items():
                cursor.execute("""
                    INSERT INTO bounding_boxes (session_id, field_name, filename, page, coordinates)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session_id,
                    field_name,
                    bbox['filename'],
                    bbox['page'],
                    json.dumps(bbox['coordinates'])
                ))
            
            # Insert citations
            for field_name, citation in citations.items():
                cursor.execute("""
                    INSERT INTO citations (session_id, field_name, citation)
                    VALUES (?, ?, ?)
                """, (session_id, field_name, citation))
            
            conn.commit()
            logger.info(f"Created session {session_id} for {application_type}")
            return session_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creating session: {e}", exc_info=True)
            raise
        finally:
            conn.close()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a complete session with all related data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get session
            cursor.execute("""
                SELECT application_type, created_at, summary_json, token_usage_json
                FROM sessions WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            application_type, created_at, summary_json, token_usage_json = row
            summary = json.loads(summary_json)
            
            # Get bounding boxes
            cursor.execute("""
                SELECT field_name, filename, page, coordinates
                FROM bounding_boxes WHERE session_id = ?
            """, (session_id,))
            
            bounding_boxes = {}
            for field_name, filename, page, coordinates in cursor.fetchall():
                bounding_boxes[field_name] = {
                    'filename': filename,
                    'page': page,
                    'coordinates': json.loads(coordinates)
                }
            
            # Get citations
            cursor.execute("""
                SELECT field_name, citation
                FROM citations WHERE session_id = ?
            """, (session_id,))
            
            citations = {field_name: citation for field_name, citation in cursor.fetchall()}
            
            # Get documents
            cursor.execute("""
                SELECT filename, file_data, mime_type
                FROM documents WHERE session_id = ?
            """, (session_id,))
            
            documents = []
            for filename, file_data, mime_type in cursor.fetchall():
                documents.append({
                    'filename': filename,
                    'content': file_data,
                    'mime_type': mime_type
                })
            
            # Reconstruct full response
            result = {
                'session_id': session_id,
                'application_type': application_type,
                'created_at': created_at,
                'summary': summary,
                'bounding_boxes': bounding_boxes,
                'citations': citations,
                'documents': documents
            }
            
            if token_usage_json:
                result['_token_usage'] = json.loads(token_usage_json)
            
            logger.info(f"Retrieved session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}", exc_info=True)
            return None
        finally:
            conn.close()
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recent sessions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT session_id, application_type, created_at
                FROM sessions
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            sessions = []
            for session_id, application_type, created_at in cursor.fetchall():
                sessions.append({
                    'session_id': session_id,
                    'application_type': application_type,
                    'created_at': created_at
                })
            
            return sessions
            
        finally:
            conn.close()
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all related data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM citations WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM bounding_boxes WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM documents WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            
            conn.commit()
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
            return False
        finally:
            conn.close()

# Global database instance
db = SessionDatabase()
