from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal


class ValidationIssue(BaseModel):
    """Represents a single validation issue found during validation."""
    field: str = Field(description="Dot notation path to the field (e.g., 'applicant.name', 'dependents[2].aadhaar')")
    severity: Literal["error", "warning", "info"] = Field(description="Severity level of the issue")
    message: str = Field(description="Human-readable explanation of the issue")
    extracted_value: Optional[Any] = Field(default=None, description="The value that was extracted")
    expected_value: Optional[Any] = Field(default=None, description="The expected value, if applicable")
    source_citation: Optional[str] = Field(default=None, description="Citation from the extraction showing where this value came from")
    requires_review: bool = Field(default=False, description="Whether this issue requires human review")


class ValidationRequest(BaseModel):
    """
    Request payload for the validation endpoint.
    
    Note: This model is used when validation is called with an existing extraction_summary.
    When called with raw files, the endpoint uses Form/File parameters instead.
    """
    application_type: str = Field(description="Type of application (e.g., 'Family Membership Certificate', 'Income Certificate')")
    extraction_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The complete JSON output from /extract-summary endpoint. Optional if files are provided."
    )


class ValidationReport(BaseModel):
    """Complete validation report for a submitted application."""
    application_type: Optional[str] = None
    auto_approved: bool = Field(description="Whether the application can be auto-approved")
    confidence_score: float = Field(description="Confidence score from 0.0 to 1.0")
    confidence_reason: Optional[str] = None
    issues: List[ValidationIssue] = Field(default_factory=list, description="List of all validation issues found")
    summary: Optional[str] = Field(default=None, description="Natural language summary of validation results")
    
    # NEW: Include full extraction results for frontend transparency
    extraction_summary: Optional[Dict[str, Any]] = None
    bounding_boxes: Optional[Dict[str, Any]] = None
    citations: Optional[Dict[str, Any]] = None
    source_documents: Optional[List[Dict[str, Any]]] = None
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the validation (e.g., rule set used, validation timestamp)"
    )
