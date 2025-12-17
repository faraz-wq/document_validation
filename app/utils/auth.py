"""
Updated authentication utilities using SQLAlchemy ORM
Handles API key validation and management with PostgreSQL
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Header, Request, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func
import hashlib
import secrets

from app.db import get_db, User, ApiKey
from app.logging_config import get_logger
from app.core.security import decode_token

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/token", auto_error=False)


def create_api_key(db: Session, user_id: int, description: str = "") -> str:
    """
    Create a new API key for a user
    Returns the plain text API key (store the hash in DB)
    """
    # Generate a random API key
    api_key = "dv_" + secrets.token_urlsafe(32)
    
    # Hash the API key for storage
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Create API key record
    db_api_key = ApiKey(
        key_hash=api_key_hash,
        owner_id=user_id,
        description=description,
        revoked=False,
        total_requests=0,
        total_errors=0,
        total_documents=0
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    logger.info(f"Created API key for user {user_id}")
    return api_key


def validate_api_key(db: Session, api_key: str) -> Optional[ApiKey]:
    """
    Validate an API key and return the ApiKey object if valid
    Returns None if invalid
    """
    if not api_key or len(api_key) < 10:
        return None
    
    try:
        # Hash the provided API key for comparison
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Query for the API key
        db_api_key = db.query(ApiKey).filter(
            ApiKey.key_hash == api_key_hash,
            ApiKey.revoked == False
        ).first()
        
        if db_api_key:
            # Update last_used_at timestamp
            db_api_key.last_used_at = func.now()
            db.commit()
            
        return db_api_key
        
    except Exception as e:
        logger.error(f"Error validating API key: {e}", exc_info=True)
        return None


def get_user_from_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency: Validate authentication via API key OR JWT token.
    Returns the authenticated user.
    """
    # 1. Try API Key first
    if x_api_key:
        api_key = validate_api_key(db, x_api_key)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API key"
            )
        
        # Set API key ID on request state for observability middleware
        request.state.api_key_id = api_key.id
        request.state.api_key = api_key
        
        # Return the user
        user = api_key.owner
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        return user

    # 2. Try JWT Token
    if token:
        payload = decode_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # No API key ID for JWT auth
        request.state.api_key_id = None
        request.state.api_key = None
        
        return user

    # 3. Neither provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide X-API-Key header or Bearer token."
    )


def get_current_admin_user(
    user: User = Depends(get_user_from_api_key)
) -> User:
    """
    FastAPI dependency: Ensure the current user is an admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user


def create_user(
    db: Session,
    email: str,
    username: str,
    is_admin: bool = False
) -> User:
    """
    Create a new user account
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == email) | (User.username == username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create user
    user = User(
        email=email,
        username=username,
        is_active=True,
        is_admin=is_admin
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"Created user: {username} ({email})")
    return user


def register_new_user_and_get_api_key(
    db: Session,
    email: str,
    username: str,
    description: str = ""
) -> tuple[User, str]:
    """
    Register a new user and return their first API key
    Returns (user, api_key)
    """
    # Create user
    user = create_user(db, email, username)
    
    # Create API key
    api_key = create_api_key(
        db,
        user.id,
        description if description else f"Initial API key for {username}"
    )
    
    return user, api_key


def list_user_api_keys(db: Session, user_id: int) -> list[ApiKey]:
    """
    List all API keys for a specific user
    """
    return db.query(ApiKey).filter(
        ApiKey.owner_id == user_id
    ).order_by(ApiKey.created_at.desc()).all()


def revoke_api_key(db: Session, user_id: int, key_id: int) -> bool:
    """
    Revoke an API key for a user
    """
    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id,
        ApiKey.owner_id == user_id
    ).first()
    
    if not api_key:
        return False
    
    api_key.revoked = True
    db.commit()
    
    logger.info(f"Revoked API key {key_id} for user {user_id}")
    return True