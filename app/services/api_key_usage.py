"""
API Key Usage Service
Centralized service for tracking document processing counts
"""

from sqlalchemy.orm import Session
from app.db import ApiKey
from app.logging_config import get_logger

logger = get_logger(__name__)


def increment_documents_for_api_key(
    db: Session,
    api_key_id: int,
    count: int = 1,
) -> None:
    """
    Increment the document counter for an API key.
    
    This should be called after successful document processing.
    
    Args:
        db: Database session
        api_key_id: ID of the API key
        count: Number of documents processed (default: 1)
    """
    try:
        api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
        if not api_key:
            logger.warning(f"API key {api_key_id} not found for document increment")
            return
        
        api_key.total_documents += count
        db.commit()
        
        logger.debug(f"Incremented document count for API key {api_key_id} by {count}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to increment document count for API key {api_key_id}: {e}", exc_info=True)
