"""
JWT-based schema management endpoints for authenticated users
/v1/me/schemas - allows dashboard users (JWT) to manage schemas they own
"""

from datetime import datetime
import sqlite3
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from pathlib import Path
import json

from app.api.v1.deps import get_current_user_from_jwt
from app.db import get_db
from app.schemas.schema_models import FieldConfig, SchemaDefinition
from app.core.schema_registry import schema_registry


router = APIRouter(prefix="/v1/me/schemas", tags=["v1-me-schemas"])


# Response models as specified in the requirements
class SchemaField(BaseModel):
    name: str
    type: str
    description: str | None
    required: bool


class SchemaDefinitionOut(BaseModel):
    schema_id: str
    schema_name: str
    description: str | None
    fields: List[SchemaField]
    created_by: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SchemaListResponse(BaseModel):
    items: List[SchemaDefinitionOut]


class CreateSchemaResponse(BaseModel):
    message: str
    schema_id: str


def _get_schema_with_updated_at(schema_id: str) -> tuple:
    """
    Helper function to get updated_at timestamp from the database
    """
    db_path = "./schemas_v1.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT created_at, updated_at
        FROM user_schemas
        WHERE schema_id = ?
    """, (schema_id,))

    result = cursor.fetchone()
    conn.close()

    if result:
        created_at_str, updated_at_str = result
        # Parse created_at
        created_at_dt = None
        if created_at_str:
            try:
                created_at_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Handle different datetime formats
                    created_at_dt = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

        # Parse updated_at
        updated_at_dt = None
        if updated_at_str:
            try:
                updated_at_dt = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Handle different datetime formats
                    updated_at_dt = datetime.strptime(updated_at_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

        return created_at_dt, updated_at_dt

    return None, None


@router.get("", response_model=SchemaListResponse)
async def list_user_schemas(
    current_user = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    List all schemas accessible to the current user (JWT authenticated)
    """
    # Convert user id to string as expected by schema_registry
    user_id = str(current_user.id)
    schemas = schema_registry.list_user_schemas(user_id)

    # Convert to the required output format
    items = []
    for schema in schemas:
        # Convert the fields to SchemaField format
        fields_out = [
            SchemaField(
                name=field.name,
                type=field.type,
                description=field.description,
                required=field.required
            )
            for field in schema.fields
        ]

        # Get timestamps from database
        created_at_dt, updated_at_dt = _get_schema_with_updated_at(schema.schema_id)

        items.append(SchemaDefinitionOut(
            schema_id=schema.schema_id,
            schema_name=schema.schema_name,
            description=schema.description,
            fields=fields_out,
            created_by=int(schema.created_by),
            created_at=created_at_dt,
            updated_at=updated_at_dt
        ))

    return SchemaListResponse(items=items)


@router.get("/{schema_id}", response_model=SchemaDefinitionOut)
async def get_user_schema(
    schema_id: str,
    current_user = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Get a specific schema that belongs to the current user
    """
    user_id = str(current_user.id)
    schema = schema_registry.get_schema(schema_id, user_id)

    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found or access denied")

    # Convert the fields to SchemaField format
    fields_out = [
        SchemaField(
            name=field.name,
            type=field.type,
            description=field.description,
            required=field.required
        )
        for field in schema.fields
    ]

    # Get timestamps from database
    created_at_dt, updated_at_dt = _get_schema_with_updated_at(schema.schema_id)

    return SchemaDefinitionOut(
        schema_id=schema.schema_id,
        schema_name=schema.schema_name,
        description=schema.description,
        fields=fields_out,
        created_by=int(schema.created_by),
        created_at=created_at_dt,
        updated_at=updated_at_dt
    )


class CreateSchemaRequest(BaseModel):
    schema_id: str
    schema_name: str
    description: str
    fields: List[FieldConfig]  # Use FieldConfig from schema models


@router.post("", response_model=CreateSchemaResponse)
async def create_user_schema(
    schema_request: CreateSchemaRequest,
    current_user = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Create a new schema for the current user
    """
    # Convert to SchemaDefinition with created_by set to current user id
    schema_def = SchemaDefinition(
        schema_id=schema_request.schema_id,
        schema_name=schema_request.schema_name,
        description=schema_request.description,
        fields=schema_request.fields,
        created_by=str(current_user.id)
    )

    success = schema_registry.register_schema(schema_def)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to register schema - ID may already exist")

    return CreateSchemaResponse(
        message="Schema created successfully",
        schema_id=schema_def.schema_id
    )


@router.put("/{schema_id}")
async def update_user_schema(
    schema_id: str,
    updates: dict,
    current_user = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Update an existing schema that belongs to the current user
    """
    user_id = str(current_user.id)
    success = schema_registry.update_schema(schema_id, user_id, updates)
    if not success:
        raise HTTPException(status_code=403, detail="Access denied or schema not found")

    return {"message": "updated"}


@router.delete("/{schema_id}")
async def delete_user_schema(
    schema_id: str,
    current_user = Depends(get_current_user_from_jwt),
    db: Session = Depends(get_db)
):
    """
    Delete a schema that belongs to the current user
    """
    user_id = str(current_user.id)
    success = schema_registry.delete_schema(schema_id, user_id)
    if not success:
        raise HTTPException(status_code=403, detail="Access denied or schema not found")

    return {"message": "deleted"}