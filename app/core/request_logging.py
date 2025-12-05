"""
Request logging middleware for observability
Tracks all API requests, response times, and errors
"""

import time
from typing import Optional
from datetime import datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.db import SessionLocal, RequestLog, ApiKey
from app.logging_config import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests to the database for observability.
    
    Tracks:
    - Request path, method, status code
    - Processing time in milliseconds
    - API key usage (if authenticated)
    - Client IP and user agent
    - Error messages (if any)
    
    This middleware MUST NOT crash requests even if logging fails.
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response = None
        error_msg: Optional[str] = None
        
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            error_msg = str(e)[:500]  # Limit error message length
            logger.exception("Unhandled exception during request")
            raise
        finally:
            # Calculate processing time
            duration_ms = (time.perf_counter() - start_time) * 1000
            status_code = response.status_code if response else 500
            
            # Extract metadata
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            
            # Get API key ID and session ID from request state (set by auth middleware)
            api_key_id = getattr(request.state, "api_key_id", None)
            session_id = getattr(request.state, "session_id", None)
            
            # Log to database (in background, never crash the request)
            self._log_request_to_db(
                api_key_id=api_key_id,
                path=request.url.path,
                method=request.method,
                status_code=status_code,
                processing_ms=duration_ms,
                error_message=error_msg,
                client_ip=client_ip,
                user_agent=user_agent,
                session_id=session_id,
            )
    
    def _log_request_to_db(
        self,
        api_key_id: Optional[int],
        path: str,
        method: str,
        status_code: int,
        processing_ms: float,
        error_message: Optional[str],
        client_ip: Optional[str],
        user_agent: Optional[str],
        session_id: Optional[str],
    ) -> None:
        """
        Log request to database.
        This method MUST handle all exceptions internally and never crash.
        """
        db: Session = SessionLocal()
        try:
            # Create request log entry
            log = RequestLog(
                api_key_id=api_key_id,
                session_id=session_id,
                path=path,
                method=method,
                status_code=status_code,
                processing_ms=processing_ms,
                error_message=error_message,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            db.add(log)
            
            # Update API key usage counters if authenticated
            if api_key_id is not None:
                api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
                if api_key:
                    api_key.total_requests += 1
                    if status_code >= 400:
                        api_key.total_errors += 1
            
            db.commit()
            
        except Exception as e:
            # NEVER crash the request due to logging failures
            db.rollback()
            logger.error(f"Failed to log request to database: {e}", exc_info=True)
        finally:
            db.close()
