"""
Service functions for user-specific metrics and statistics
Provides functionality to get user's API key usage and request time-series data
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.db.models import ApiKey, RequestLog
from app.schemas.user_metrics import PerKeyStats, UserDashboardStats, UserRequestBucket
from enum import Enum


def get_user_aggregate_stats(db: Session, user_id: int) -> UserDashboardStats:
    """
    Get aggregate statistics for a specific user across all their API keys
    """
    # Get the user's API key IDs
    key_ids = [
        key_id[0] for key_id in 
        db.query(ApiKey.id)
        .filter(ApiKey.owner_id == user_id)
        .all()
    ]
    
    if not key_ids:
        # Return empty stats if user has no API keys
        return UserDashboardStats(
            total_requests=0,
            total_errors=0,
            total_documents=0,
            avg_response_time_ms=None,
            requests_last_24h=0,
            errors_last_24h=0,
            per_key=[]
        )
    
    # Aggregates over ApiKey table for this user
    agg = (
        db.query(
            func.coalesce(func.sum(ApiKey.total_requests), 0),
            func.coalesce(func.sum(ApiKey.total_errors), 0),
            func.coalesce(func.sum(ApiKey.total_documents), 0),
        )
        .filter(ApiKey.owner_id == user_id)
        .one()
    )
    
    total_requests, total_errors, total_documents = agg
    
    # Calculate 24-hour stats from RequestLog
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    
    # Calculate 24-hour request stats
    recent_stats = (
        db.query(
            func.count(RequestLog.id),
            func.sum(case((RequestLog.status_code >= 400, 1), else_=0))
        )
        .filter(
            RequestLog.api_key_id.in_(key_ids),
            RequestLog.timestamp >= twenty_four_hours_ago
        )
        .one()
    )
    
    requests_last_24h, errors_last_24h = recent_stats
    requests_last_24h = requests_last_24h or 0
    errors_last_24h = errors_last_24h or 0
    
    # Calculate average response time
    avg_response_time_result = (
        db.query(func.avg(RequestLog.processing_ms))
        .filter(RequestLog.api_key_id.in_(key_ids))
        .scalar()
    )
    
    avg_response_time_ms = float(avg_response_time_result) if avg_response_time_result is not None else None
    
    # Get per-key stats
    per_key_query = (
        db.query(
            ApiKey.id,
            ApiKey.description,
            ApiKey.total_requests,
            ApiKey.total_errors,
            ApiKey.total_documents,
            ApiKey.last_used_at
        )
        .filter(ApiKey.owner_id == user_id)
        .all()
    )
    
    per_key_stats = [
        PerKeyStats(
            api_key_id=api_key.id,
            description=api_key.description,
            total_requests=api_key.total_requests,
            total_errors=api_key.total_errors,
            total_documents=api_key.total_documents,
            last_used_at=api_key.last_used_at
        )
        for api_key in per_key_query
    ]
    
    return UserDashboardStats(
        total_requests=total_requests,
        total_errors=total_errors,
        total_documents=total_documents,
        avg_response_time_ms=avg_response_time_ms,
        requests_last_24h=requests_last_24h,
        errors_last_24h=errors_last_24h,
        per_key=per_key_stats
    )


def get_user_request_timeseries(
    db: Session,
    user_id: int,
    start: datetime,
    end: datetime,
    group_by: str  # "hour" or "day"
) -> List[UserRequestBucket]:
    """
    Get time-series metrics for a user's API requests
    """
    # Get the user's API key IDs
    key_ids = [
        key_id[0] for key_id in 
        db.query(ApiKey.id)
        .filter(ApiKey.owner_id == user_id)
        .all()
    ]
    
    if not key_ids:
        return []
    
    # Define the grouping expression based on the group_by parameter
    if group_by == "hour":
        bucket_expr = func.date_trunc('hour', RequestLog.timestamp)
    elif group_by == "day":
        bucket_expr = func.date_trunc('day', RequestLog.timestamp)
    else:
        raise ValueError("group_by must be either 'hour' or 'day'")
    
    # Query to get time-series data
    query = (
        db.query(
            bucket_expr.label("bucket"),
            func.count(RequestLog.id).label("requests"),
            func.sum(case((RequestLog.status_code >= 400, 1), else_=0)).label("errors"),
            func.avg(RequestLog.processing_ms).label("avg_ms"),
        )
        .filter(
            RequestLog.api_key_id.in_(key_ids),
            RequestLog.timestamp >= start,
            RequestLog.timestamp <= end,
        )
        .group_by(bucket_expr)
        .order_by(bucket_expr)
        .all()
    )
    
    # Convert query results to UserRequestBucket objects
    result = []
    for row in query:
        bucket, requests, errors, avg_ms = row
        result.append(
            UserRequestBucket(
                bucket=bucket,
                requests=requests or 0,
                errors=errors or 0,
                avg_ms=float(avg_ms) if avg_ms is not None else None
            )
        )
    
    return result