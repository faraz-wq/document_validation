"""
V1 API routes for user-specific request logs
Endpoint for /v1/me/logs
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user_from_jwt
from app.db import get_db
from app.services.user_logs import get_user_logs, UserLogFilters, UserLogResponse
from app.db.models import User

router = APIRouter(prefix="/me", tags=["User Logs"])


@router.get("/logs", response_model=UserLogResponse)
async def get_user_logs_endpoint(
    current_user: User = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    errors_only: bool = Query(False, description="Only return logs with 4xx or 5xx status codes"),
    min_processing_ms: float = Query(None, ge=0, description="Minimum processing time in milliseconds"),
    path_contains: str = Query(None, description="Filter logs by path containing this string"),
):
    """
    Get request logs for the current user
    """
    filters = UserLogFilters(
        limit=limit,
        offset=offset,
        errors_only=errors_only,
        min_processing_ms=min_processing_ms,
        path_contains=path_contains
    )
    
    result = get_user_logs(db, current_user.id, filters)
    return result