"""
Admin Dashboard API Router
Provides endpoints for monitoring API usage, request logs, and system statistics
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional

from app.db import get_db, ApiKey, RequestLog, User
from app.schemas.dashboard import (
    ApiKeyUsageSummary,
    ApiKeyUsageListResponse,
    RequestLogItem,
    RequestLogResponse,
    DashboardStats,
)
from app.utils.auth import get_current_admin_user

router = APIRouter(prefix="/v1/admin", tags=["Admin Dashboard"])


@router.get("/api-keys/usage", response_model=ApiKeyUsageListResponse)
def get_api_keys_usage(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    include_revoked: bool = Query(False, description="Include revoked API keys"),
):
    """
    Get usage statistics for all API keys.
    Admin only.
    """
    query = db.query(ApiKey)
    
    if not include_revoked:
        query = query.filter(ApiKey.revoked == False)
    
    api_keys = query.all()
    
    items = []
    for key in api_keys:
        total_req = key.total_requests or 0
        total_err = key.total_errors or 0
        error_rate = (total_err / total_req) if total_req > 0 else 0.0
        
        owner_email = key.owner.email if key.owner else None
        owner_username = key.owner.username if key.owner else None
        
        items.append(
            ApiKeyUsageSummary(
                api_key_id=key.id,
                owner_id=key.owner_id,
                owner_email=owner_email,
                owner_username=owner_username,
                description=key.description,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                revoked=key.revoked,
                total_requests=total_req,
                total_errors=total_err,
                error_rate=error_rate,
                total_documents=key.total_documents or 0,
            )
        )
    
    return ApiKeyUsageListResponse(items=items, total_count=len(items))


@router.get("/logs", response_model=RequestLogResponse)
def get_request_logs(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    api_key_id: Optional[int] = Query(None, description="Filter by API key ID"),
    errors_only: bool = Query(False, description="Show only error responses (4xx, 5xx)"),
    min_processing_ms: Optional[float] = Query(None, description="Filter by minimum processing time"),
    path_contains: Optional[str] = Query(None, description="Filter by path substring"),
):
    """
    Get request logs with filtering options.
    Admin only.
    """
    query = db.query(RequestLog).order_by(RequestLog.timestamp.desc())
    
    # Apply filters
    if api_key_id is not None:
        query = query.filter(RequestLog.api_key_id == api_key_id)
    
    if errors_only:
        query = query.filter(RequestLog.status_code >= 400)
    
    if min_processing_ms is not None:
        query = query.filter(RequestLog.processing_ms >= min_processing_ms)
    
    if path_contains:
        query = query.filter(RequestLog.path.contains(path_contains))
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply pagination
    logs = query.offset(offset).limit(limit).all()
    
    items = [
        RequestLogItem(
            id=log.id,
            api_key_id=log.api_key_id,
            session_id=log.session_id,
            path=log.path,
            method=log.method,
            status_code=log.status_code,
            processing_ms=log.processing_ms,
            timestamp=log.timestamp,
            client_ip=log.client_ip,
            user_agent=log.user_agent,
            error_message=log.error_message,
        )
        for log in logs
    ]
    
    return RequestLogResponse(items=items, total_count=total_count)


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
):
    """
    Get overall dashboard statistics.
    Admin only.
    """
    # Total API keys
    total_api_keys = db.query(func.count(ApiKey.id)).scalar()
    active_api_keys = db.query(func.count(ApiKey.id)).filter(
        ApiKey.revoked == False
    ).scalar()
    
    # Sum of all usage counters
    usage_stats = db.query(
        func.sum(ApiKey.total_requests).label('total_requests'),
        func.sum(ApiKey.total_errors).label('total_errors'),
        func.sum(ApiKey.total_documents).label('total_documents'),
    ).first()
    
    total_requests = usage_stats.total_requests or 0
    total_errors = usage_stats.total_errors or 0
    total_documents = usage_stats.total_documents or 0
    
    # Average response time
    avg_response_time = db.query(
        func.avg(RequestLog.processing_ms)
    ).scalar() or 0.0
    
    # Last 24 hours stats
    last_24h = datetime.utcnow() - timedelta(hours=24)
    requests_last_24h = db.query(func.count(RequestLog.id)).filter(
        RequestLog.timestamp >= last_24h
    ).scalar() or 0
    
    errors_last_24h = db.query(func.count(RequestLog.id)).filter(
        and_(
            RequestLog.timestamp >= last_24h,
            RequestLog.status_code >= 400
        )
    ).scalar() or 0
    
    return DashboardStats(
        total_requests=total_requests,
        total_errors=total_errors,
        total_documents=total_documents,
        total_api_keys=total_api_keys,
        active_api_keys=active_api_keys,
        avg_response_time_ms=avg_response_time,
        requests_last_24h=requests_last_24h,
        errors_last_24h=errors_last_24h,
    )
