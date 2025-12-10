"""
V1 API routes for user-specific statistics
Endpoints for /v1/me/stats and /v1/me/metrics/requests
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user_from_jwt
from app.db import get_db
from app.services.user_metrics import get_user_aggregate_stats, get_user_request_timeseries
from app.schemas.user_metrics import UserDashboardStats, UserRequestBucket
from app.db.models import User

router = APIRouter(prefix="/me", tags=["User Stats & Metrics"])


@router.get("/stats", response_model=UserDashboardStats)
async def get_user_stats(
    current_user: User = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db),
):
    """
    Get dashboard statistics for the current user
    """
    stats = get_user_aggregate_stats(db, current_user.id)
    return stats


@router.get("/metrics/requests", response_model=list[UserRequestBucket])
async def get_user_request_metrics(
    current_user: User = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db),
    start: Optional[datetime] = Query(None, description="Start datetime for the time series"),
    end: Optional[datetime] = Query(None, description="End datetime for the time series"),
    group_by: str = Query("day", pattern="^(hour|day)$", description="Group by hour or day"),
):
    """
    Get time-series metrics for the current user's API requests
    """
    # Set default values if not provided
    if end is None:
        end = datetime.utcnow()
    if start is None:
        start = end - timedelta(days=7)  # Default to last 7 days

    # Ensure start is not after end
    if start > end:
        start = end - timedelta(days=7)

    metrics = get_user_request_timeseries(
        db, current_user.id, start, end, group_by
    )
    return metrics