"""
Google Cloud Storage utility for document storage.
Handles uploading, downloading, and managing documents in GCS.
"""

import os
from typing import Optional, BinaryIO
from google.cloud import storage
from google.cloud.exceptions import NotFound
from app.logging_config import get_logger
from pathlib import Path
import mimetypes

logger = get_logger(__name__)


class GCSStorage:
    """
    Google Cloud Storage manager for document files.
    
    Configuration via environment variables:
    - GCS_BUCKET_NAME: Name of the GCS bucket (required)
    - GCS_DOCUMENTS_PREFIX: Prefix/folder for documents (default: 'documents/')
    - GOOGLE_APPLICATION_CREDENTIALS: Path to service account key (optional if using default credentials)
    """
    
    def __init__(self):
        self.bucket_name = os.getenv("GCS_BUCKET_NAME")
        self.documents_prefix = os.getenv("GCS_DOCUMENTS_PREFIX", "documents/")
        
        if not self.bucket_name:
            raise ValueError("GCS_BUCKET_NAME environment variable is required")
        
        # Ensure prefix ends with /
        if self.documents_prefix and not self.documents_prefix.endswith('/'):
            self.documents_prefix += '/'
        
        try:
            # Initialize GCS client
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
            
            logger.info(f"GCS Storage initialized: bucket={self.bucket_name}, prefix={self.documents_prefix}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}", exc_info=True)
            raise ValueError(f"Failed to initialize GCS storage: {str(e)}")
    
    def upload_document(
        self, 
        file_content: bytes, 
        session_id: str, 
        filename: str,
        mime_type: Optional[str] = None
    ) -> str:
        """
        Upload a document to GCS.
        
        Args:
            file_content: Binary content of the file
            session_id: Session ID (used for organizing files)
            filename: Original filename
            mime_type: MIME type of the file (auto-detected if not provided)
        
        Returns:
            GCS path (blob name) of the uploaded file
        
        Raises:
            Exception: If upload fails
        """
        # Sanitize filename
        safe_filename = Path(filename).name
        
        # Construct GCS path: documents/{session_id}/{filename}
        gcs_path = f"{self.documents_prefix}{session_id}/{safe_filename}"
        
        # Auto-detect MIME type if not provided
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(filename)
            mime_type = mime_type or 'application/octet-stream'
        
        try:
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_string(
                file_content,
                content_type=mime_type
            )
            
            logger.info(f"Uploaded document to GCS: {gcs_path} ({len(file_content)} bytes)")
            return gcs_path
            
        except Exception as e:
            logger.error(f"Failed to upload document to GCS: {gcs_path}, error: {e}", exc_info=True)
            raise Exception(f"GCS upload failed: {str(e)}")
    
    def download_document(self, gcs_path: str) -> bytes:
        """
        Download a document from GCS.
        
        Args:
            gcs_path: GCS path (blob name) of the file
        
        Returns:
            Binary content of the file
        
        Raises:
            NotFound: If file doesn't exist
            Exception: If download fails
        """
        try:
            blob = self.bucket.blob(gcs_path)
            content = blob.download_as_bytes()
            
            logger.info(f"Downloaded document from GCS: {gcs_path} ({len(content)} bytes)")
            return content
            
        except NotFound:
            logger.error(f"Document not found in GCS: {gcs_path}")
            raise NotFound(f"Document not found: {gcs_path}")
        except Exception as e:
            logger.error(f"Failed to download document from GCS: {gcs_path}, error: {e}", exc_info=True)
            raise Exception(f"GCS download failed: {str(e)}")
    
    def delete_document(self, gcs_path: str) -> bool:
        """
        Delete a document from GCS.
        
        Args:
            gcs_path: GCS path (blob name) of the file
        
        Returns:
            True if deleted, False if file didn't exist
        
        Raises:
            Exception: If deletion fails
        """
        try:
            blob = self.bucket.blob(gcs_path)
            blob.delete()
            
            logger.info(f"Deleted document from GCS: {gcs_path}")
            return True
            
        except NotFound:
            logger.warning(f"Document not found for deletion: {gcs_path}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete document from GCS: {gcs_path}, error: {e}", exc_info=True)
            raise Exception(f"GCS deletion failed: {str(e)}")
    
    def delete_session_documents(self, session_id: str) -> int:
        """
        Delete all documents for a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            Number of documents deleted
        """
        prefix = f"{self.documents_prefix}{session_id}/"
        
        try:
            blobs = list(self.bucket.list_blobs(prefix=prefix))
            count = 0
            
            for blob in blobs:
                blob.delete()
                count += 1
            
            logger.info(f"Deleted {count} documents for session {session_id}")
            return count
            
        except Exception as e:
            logger.error(f"Failed to delete session documents: {session_id}, error: {e}", exc_info=True)
            raise Exception(f"GCS batch deletion failed: {str(e)}")
    
    def get_signed_url(
        self, 
        gcs_path: str, 
        expiration_minutes: int = 60
    ) -> str:
        """
        Generate a signed URL for temporary access to a document.
        
        Args:
            gcs_path: GCS path (blob name) of the file
            expiration_minutes: URL expiration time in minutes (default: 60)
        
        Returns:
            Signed URL
        
        Raises:
            Exception: If URL generation fails
        """
        try:
            blob = self.bucket.blob(gcs_path)
            url = blob.generate_signed_url(
                version="v4",
                expiration=expiration_minutes * 60,  # Convert to seconds
                method="GET"
            )
            
            logger.info(f"Generated signed URL for: {gcs_path} (expires in {expiration_minutes}m)")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {gcs_path}, error: {e}", exc_info=True)
            raise Exception(f"Signed URL generation failed: {str(e)}")
    
    def document_exists(self, gcs_path: str) -> bool:
        """
        Check if a document exists in GCS.
        
        Args:
            gcs_path: GCS path (blob name) of the file
        
        Returns:
            True if exists, False otherwise
        """
        try:
            blob = self.bucket.blob(gcs_path)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking document existence: {gcs_path}, error: {e}")
            return False


# Singleton instance
_gcs_storage: Optional[GCSStorage] = None


def get_gcs_storage() -> Optional[GCSStorage]:
    """
    Get or create the GCS storage singleton instance.
    
    Returns:
        GCSStorage instance if GCS is enabled, None otherwise
    """
    global _gcs_storage
    
    # If GCS is not enabled, return None
    if not is_gcs_enabled():
        logger.info("GCS storage is not enabled (GCS_BUCKET_NAME not set)")
        return None
    
    if _gcs_storage is None:
        try:
            _gcs_storage = GCSStorage()
        except Exception as e:
            logger.error(f"Failed to initialize GCS storage: {e}", exc_info=True)
            return None
    
    return _gcs_storage


def is_gcs_enabled() -> bool:
    """
    Check if GCS storage is enabled (GCS_BUCKET_NAME is set).
    
    Returns:
        True if GCS is enabled, False otherwise
    """
    return bool(os.getenv("GCS_BUCKET_NAME"))
