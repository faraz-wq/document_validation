from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from app.verification.schema import (
    VerificationReport as ValidationReport,
    ValidationIssue,
    FieldEntity,
    FieldRelationship,
    SchemaProjection,
    ValidationSummary,
    UniversalExtractionResponse # Keeping this if needed for compatibility, though it's aliased to VerificationReport
)

# Canonical Response Model alias
# ValidationReport is the primary model used by the endpoint
# It inherits from VerificationReport in schema.py

class ValidationRequest(BaseModel):
    """
    Request payload for the validation endpoint.
    Used when validation is called with an existing extraction_summary.
    """
    application_type: str = Field(description="Type of application (e.g., 'Family Membership Certificate')")
    extraction_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The complete JSON output from /extract-summary endpoint."
    )
