from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class KeyDetailDefinition(BaseModel):
    """
    Static Input 1: Key details that are needed to be identified.
    Maps a field to its semantic requirement and mandatory proof sources.
    """
    field_path: str
    display_name: str
    description: str
    is_mandatory: bool = True
    valid_proof_documents: List[str] = [] # e.g. ["Aadhaar Card", "Voter ID"]

class ValidationRuleDefinition(BaseModel):
    """
    Static Input 2: Rules that these fields must follow.
    Defines logical constraints and cross-field consistency checks.
    """
    rule_id: str
    description: str
    severity: str = "error" # error, warning, info
    rule_type: str # e.g. "consistency", "format", "range"
    fields_involved: List[str]

class VerificationConfig(BaseModel):
    """
    The unified configuration for a specific application type.
    """
    application_type: str
    key_details: List[KeyDetailDefinition]
    rules: List[ValidationRuleDefinition]

class VerificationIssue(BaseModel):
    field: Optional[str] = None
    rule_id: Optional[str] = None
    severity: str
    message: str
    passed: bool = False

class VerificationReport(BaseModel):
    application_type: str
    report_id: str
    timestamp: str
    overall_status: str # "verified", "flagged", "failed"
    confidence_score: float = 0.0
    summary: Optional[str] = None
    confidence_reason: Optional[str] = None
    issues: List[VerificationIssue]
    
    # NEW: Include full extraction results for frontend transparency
    extraction_summary: Dict[str, Any] = {}
    bounding_boxes: Dict[str, Any] = {}
    citations: Dict[str, Any] = {}
    source_documents: List[Dict[str, Any]] = []
    
    metadata: Dict[str, Any] = {}
