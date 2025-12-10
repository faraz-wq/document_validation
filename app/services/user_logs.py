"""
Service functions for user-specific request logs
Provides functionality for users to view their own request logs based on their API keys
"""

from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import RequestLog, ApiKey
from pydantic import BaseModel, Field


class UserLogFilters(BaseModel):
    limit: int = 100
    offset: int = 0
    errors_only: bool = False
    min_processing_ms: float | None = None
    path_contains: str | None = None


class UserLogItem(BaseModel):
    id: int
    api_key_id: int | None
    session_id: str | None
    method: str
    path: str
    status_code: int
    processing_ms: float
    timestamp: datetime
    client_ip: str | None
    user_agent: str | None
    error_message: str | None


class UserLogResponse(BaseModel):
    items: List[UserLogItem]
    total_count: int


def get_user_logs(
    db: Session,
    user_id: int,
    filters: UserLogFilters,
) -> UserLogResponse:
    """
    Get request logs for a specific user based on their API keys
    """
    # Start building the query with a join on ApiKey
    q = (
        db.query(RequestLog)
        .join(ApiKey, ApiKey.id == RequestLog.api_key_id)
        .filter(ApiKey.owner_id == user_id)
    )

    # Apply filters
    if filters.errors_only:
        q = q.filter(RequestLog.status_code >= 400)
    
    if filters.min_processing_ms is not None:
        q = q.filter(RequestLog.processing_ms >= filters.min_processing_ms)
    
    if filters.path_contains is not None:
        q = q.filter(RequestLog.path.contains(filters.path_contains))

    # Get total count before applying pagination
    total_count = q.count()

    # Apply ordering and pagination
    items = q.order_by(RequestLog.timestamp.desc()).offset(filters.offset).limit(filters.limit).all()

    # Convert to response format
    log_items = [
        UserLogItem(
            id=log.id,
            api_key_id=log.api_key_id,
            session_id=log.session_id,
            method=log.method,
            path=log.path,
            status_code=log.status_code,
            processing_ms=log.processing_ms,
            timestamp=log.timestamp,
            client_ip=log.client_ip,
            user_agent=log.user_agent,
            error_message=log.error_message
        )
        for log in items
    ]

    return UserLogResponse(
        items=log_items,
        total_count=total_count
    )