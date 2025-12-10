"""
Pydantic schemas for user-specific metrics and statistics
Used for API responses showing individual user's API key usage and request metrics
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


from pydantic import ConfigDict

class PerKeyStats(BaseModel):
    """Statistics for an individual API key belonging to the user"""
    api_key_id: int
    description: Optional[str] = None
    total_requests: int
    total_errors: int
    total_documents: int
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserDashboardStats(BaseModel):
    """Dashboard statistics for a specific user"""
    total_requests: int
    total_errors: int
    total_documents: int
    avg_response_time_ms: Optional[float] = None
    requests_last_24h: int
    errors_last_24h: int
    per_key: List[PerKeyStats]


class UserRequestBucket(BaseModel):
    """Time-series bucket for user request metrics"""
    bucket: datetime
    requests: int
    errors: int
    avg_ms: Optional[float] = None