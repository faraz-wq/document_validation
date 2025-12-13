"""
Dependencies for v1 API routes
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Annotated

from app.db import get_db, User
from app.core.security import decode_token
from app.db.models import User as UserModel

# Simple JWT authentication scheme
bearer_scheme = HTTPBearer()

def get_current_user_from_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> UserModel:
    """
    Get current user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user