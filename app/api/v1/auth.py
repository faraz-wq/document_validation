"""
Auth endpoints for v1 API (JWT-based authentication)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Literal
from pydantic import BaseModel, EmailStr, constr

from app.db import get_db
from app.db.models import User as UserModel
from app.utils.passwords import hash_password, verify_password
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.utils.auth import create_api_key

router = APIRouter(prefix="/v1/auth", tags=["v1-auth"])


# Pydantic models
class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str
    is_admin: bool

class RegisterRequest(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=50)
    password: constr(min_length=8)

class RegisterResponse(BaseModel):
    user: UserOut
    api_key: str | None = None  # only if created

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    user: UserOut

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]


@router.post("/register", response_model=RegisterResponse)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user with email, username, and password
    """
    # Check if user with same email or username already exists
    existing_user = db.query(UserModel).filter(
        (UserModel.email == request.email) | (UserModel.username == request.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    hashed_password = hash_password(request.password)
    
    user = UserModel(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Optionally create an API key for the user
    api_key = None
    try:
        # Call the existing create_api_key function without modifying its behavior
        api_key = create_api_key(db, user.id, description="default")
    except Exception:
        # If API key creation fails, still return the user (don't fail the registration)
        pass
    
    user_out = UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        is_admin=user.is_admin
    )
    
    return RegisterResponse(user=user_out, api_key=api_key)


@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password, returns JWT tokens
    """
    # Fetch user by email
    user = db.query(UserModel).filter(UserModel.email == request.email).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or user is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access and refresh tokens
    access_token_data = {
        "sub": str(user.id),
        "email": user.email,
        "is_admin": user.is_admin
    }
    
    refresh_token_data = {
        "sub": str(user.id),
        "type": "refresh"
    }
    
    access_token = create_access_token(access_token_data)
    refresh_token = create_refresh_token(refresh_token_data)
    
    user_out = UserOut(
        id=user.id,
        email=user.email,
        username=user.username,
        is_admin=user.is_admin
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_out
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(
    request: TokenRefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    payload = decode_token(request.refresh_token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user and ensure active
    user = db.query(UserModel).filter(UserModel.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue new access token only
    access_token_data = {
        "sub": str(user.id),
        "email": user.email,
        "is_admin": user.is_admin
    }

    new_access_token = create_access_token(access_token_data)

    return TokenRefreshResponse(
        access_token=new_access_token,
        token_type="bearer"
    )


@router.post("/logout")
def logout(
    request: TokenRefreshRequest = None  # Optionally accept refresh token for soft invalidation
):
    """
    Logout endpoint (stateless for now)
    """
    # For now, stateless logout - in future we could implement token blacklisting
    # if request.refresh_token is provided, we could add it to a blacklist
    return {"message": "ok"}