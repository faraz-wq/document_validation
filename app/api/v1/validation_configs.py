from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pydantic import BaseModel
import json
import os
from pathlib import Path

from app.verification.schema import VerificationConfig, KeyDetailDefinition, ValidationRuleDefinition
from app.verification import registry
from app.api.v1.deps import get_current_user_from_jwt

router = APIRouter()

# Path to store custom configurations
CUSTOM_CONFIGS_DIR = Path("data/custom_configs")
CUSTOM_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)


class ValidationConfigResponse(BaseModel):
    configs: List[VerificationConfig]


@router.get("/validation-configs", response_model=ValidationConfigResponse)
async def list_validation_configs(current_user = Depends(get_current_user_from_jwt)):
    """
    List all available validation configurations (built-in + custom)
    """
    configs = []
    
    # Get built-in configs from registry
    for app_type, config in registry.VERIFICATION_REGISTRY.items():
        configs.append(config)
    
    # Get custom configs from file system
    for config_file in CUSTOM_CONFIGS_DIR.glob("*.json"):
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
                config = VerificationConfig(**config_data)
                # Only add if not already in registry (custom configs override)
                if config.application_type not in registry.VERIFICATION_REGISTRY:
                    configs.append(config)
        except Exception as e:
            # Log error but continue
            print(f"Error loading config from {config_file}: {e}")
    
    return {"configs": configs}


@router.get("/validation-configs/{application_type}", response_model=VerificationConfig)
async def get_validation_config(
    application_type: str,
    current_user = Depends(get_current_user_from_jwt)
):
    """
    Get a specific validation configuration by application type
    """
    # Check registry first
    config = registry.get_verification_config(application_type)
    if config:
        return config
    
    # Check custom configs
    config_file = CUSTOM_CONFIGS_DIR / f"{application_type.replace(' ', '_')}.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            return VerificationConfig(**config_data)
    
    raise HTTPException(status_code=404, detail=f"Configuration for '{application_type}' not found")


@router.post("/validation-configs", response_model=VerificationConfig)
async def create_validation_config(
    config: VerificationConfig,
    current_user = Depends(get_current_user_from_jwt)
):
    """
    Create a new custom validation configuration
    """
    # Check if already exists
    if config.application_type in registry.VERIFICATION_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Configuration for '{config.application_type}' already exists as a built-in config"
        )
    
    config_file = CUSTOM_CONFIGS_DIR / f"{config.application_type.replace(' ', '_')}.json"
    if config_file.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Configuration for '{config.application_type}' already exists"
        )
    
    # Save to file
    with open(config_file, 'w') as f:
        json.dump(config.model_dump(), f, indent=2)
    
    # Register in runtime registry
    registry.register_config(config)
    
    return config


@router.put("/validation-configs/{application_type}", response_model=VerificationConfig)
async def update_validation_config(
    application_type: str,
    config: VerificationConfig,
    current_user = Depends(get_current_user_from_jwt)
):
    """
    Update an existing custom validation configuration
    """
    # Don't allow updating built-in configs
    if application_type in registry.VERIFICATION_REGISTRY:
        # Check if it's a custom override
        config_file = CUSTOM_CONFIGS_DIR / f"{application_type.replace(' ', '_')}.json"
        if not config_file.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Cannot modify built-in configuration '{application_type}'. Create a new one instead."
            )
    
    # Ensure application_type matches
    if config.application_type != application_type:
        raise HTTPException(
            status_code=400,
            detail="Application type in URL must match application type in config"
        )
    
    config_file = CUSTOM_CONFIGS_DIR / f"{application_type.replace(' ', '_')}.json"
    
    # Save to file
    with open(config_file, 'w') as f:
        json.dump(config.model_dump(), f, indent=2)
    
    # Update runtime registry
    registry.register_config(config)
    
    return config


@router.delete("/validation-configs/{application_type}")
async def delete_validation_config(
    application_type: str,
    current_user = Depends(get_current_user_from_jwt)
):
    """
    Delete a custom validation configuration
    """
    # Don't allow deleting built-in configs
    if application_type in registry.VERIFICATION_REGISTRY:
        config_file = CUSTOM_CONFIGS_DIR / f"{application_type.replace(' ', '_')}.json"
        if not config_file.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete built-in configuration '{application_type}'"
            )
    
    config_file = CUSTOM_CONFIGS_DIR / f"{application_type.replace(' ', '_')}.json"
    
    if not config_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Configuration for '{application_type}' not found"
        )
    
    # Delete file
    config_file.unlink()
    
    # Remove from runtime registry
    if application_type in registry.VERIFICATION_REGISTRY:
        del registry.VERIFICATION_REGISTRY[application_type]
    
    return {"message": f"Configuration '{application_type}' deleted successfully"}


@router.get("/validation-configs/{application_type}/export")
async def export_validation_config(
    application_type: str,
    current_user = Depends(get_current_user_from_jwt)
):
    """
    Export a validation configuration as JSON for download/sharing
    """
    config = registry.get_verification_config(application_type)
    if not config:
        # Check custom configs
        config_file = CUSTOM_CONFIGS_DIR / f"{application_type.replace(' ', '_')}.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail=f"Configuration for '{application_type}' not found")
    
    return config.model_dump()
