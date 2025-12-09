from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.v1.deps import get_current_user_from_jwt
from app.db.models import User as UserModel
from app.utils.auth import create_api_key, list_user_api_keys, revoke_api_key


router = APIRouter(prefix="/me/api-keys", tags=["v1-me-api-keys"])


# Response models
class ApiKeyItem(BaseModel):
    id: int
    description: str | None
    created_at: datetime
    last_used_at: datetime | None
    revoked: bool
    total_requests: int
    total_errors: int
    total_documents: int


class ApiKeyListResponse(BaseModel):
    items: List[ApiKeyItem]


# Request model for creating API key
class CreateApiKeyRequest(BaseModel):
    description: str | None = None


# Response model for creating API key
class CreateApiKeyResponse(BaseModel):
    api_key: str  # plaintext, shown once
    id: int       # ApiKey.id from DB
    message: str = "API key created"


# Response model for deleting API key
class DeleteApiKeyResponse(BaseModel):
    message: str


@router.get("/", response_model=ApiKeyListResponse)
def list_user_api_keys_endpoint(
    current_user: UserModel = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    List all API keys for the current user.
    Only returns API keys that belong to the authenticated user.
    """
    api_keys = list_user_api_keys(db, current_user.id)
    
    items = []
    for api_key in api_keys:
        items.append(ApiKeyItem(
            id=api_key.id,
            description=api_key.description,
            created_at=api_key.created_at,
            last_used_at=api_key.last_used_at,
            revoked=api_key.revoked,
            total_requests=api_key.total_requests,
            total_errors=api_key.total_errors,
            total_documents=api_key.total_documents
        ))
    
    return ApiKeyListResponse(items=items)


@router.post("/", response_model=CreateApiKeyResponse)
def create_user_api_key(
    request: CreateApiKeyRequest,
    current_user: UserModel = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Create a new API key for the current user.
    The API key is returned in plaintext only once and should be stored securely by the client.
    """
    api_key_plaintext = create_api_key(
        db,
        user_id=current_user.id,
        description=request.description or ""
    )

    # Get the API key from the database to get its ID
    # Since create_api_key only returns the plaintext, we need to fetch the key record
    # that was just created by filtering for the most recently created key for this user
    from app.db.models import ApiKey
    newest_key = db.query(ApiKey).filter(
        ApiKey.owner_id == current_user.id
    ).order_by(ApiKey.created_at.desc()).first()

    if not newest_key:
        # This should not happen if create_api_key succeeded, but just in case
        raise HTTPException(
            status_code=500,
            detail="Error retrieving the created API key"
        )

    return CreateApiKeyResponse(
        api_key=api_key_plaintext,
        id=newest_key.id,
        message="API key created"
    )


@router.delete("/{key_id}", response_model=DeleteApiKeyResponse)
def revoke_user_api_key(
    key_id: int,
    current_user: UserModel = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Revoke an API key owned by the current user.
    Returns 404 if the API key doesn't exist or doesn't belong to the user.
    """
    success = revoke_api_key(db, current_user.id, key_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="API key not found or not owned by user"
        )
    
    return DeleteApiKeyResponse(message="API key revoked")