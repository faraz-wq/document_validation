"""
Pydantic schemas for the Admin Dashboard
Used for API responses showing usage statistics and request logs
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ApiKeyUsageSummary(BaseModel):
    """Summary of API key usage statistics"""
    api_key_id: int
    owner_id: int
    owner_email: Optional[str] = None
    owner_username: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    revoked: bool
    total_requests: int
    total_errors: int
    error_rate: float = Field(description="Error rate as a decimal (0.0 to 1.0)")
    total_documents: int
    
    class Config:
        from_attributes = True


class ApiKeyUsageListResponse(BaseModel):
    """List of API key usage summaries"""
    items: List[ApiKeyUsageSummary]
    total_count: int


class RequestLogItem(BaseModel):
    """Individual request log entry"""
    id: int
    api_key_id: Optional[int] = None
    session_id: Optional[str] = None
    path: str
    method: str
    status_code: int
    processing_ms: float
    timestamp: datetime
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class RequestLogResponse(BaseModel):
    """List of request log entries"""
    items: List[RequestLogItem]
    total_count: int
    
    
class DashboardStats(BaseModel):
    """Overall dashboard statistics"""
    total_requests: int
    total_errors: int
    total_documents: int
    total_api_keys: int
    active_api_keys: int
    avg_response_time_ms: float
    requests_last_24h: int
    errors_last_24h: int
