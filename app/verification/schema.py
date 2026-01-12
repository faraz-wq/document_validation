from typing import List, Dict, Any, Optional, Literal
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
    nested_fields: Optional[List['KeyDetailDefinition']] = None

KeyDetailDefinition.model_rebuild()

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

# --- CANONICAL SCHEMA-LAST RESPONSE MODELS ---

class ValidationIssue(BaseModel):
    """
    Represents a validation issue (Strict Schema-Last).
    REFERENCE ONLY schema_field and field_ids. No raw values.
    """
    schema_field: str = Field(description="The schema field path related to this issue")
    severity: Literal["error", "warning"] = Field(description="Severity grade")
    message: str = Field(description="Human-readable explanation")
    related_field_ids: List[str] = Field(default_factory=list, description="IDs of fields involved in this issue")
    requires_review: bool = Field(default=False)

class SupportsItem(BaseModel):
    application_field: str
    support_type: str

class ValidationRequirements(BaseModel):
    required_proofs: List[str] = []
    rules: List[str] = []

class FieldEntity(BaseModel):
    field_id: str
    field_name: str
    field_value: Optional[Any]
    document: Dict[str, Any]  # {filename, document_type, page}
    citation: Dict[str, Any]  # {bounding_box, text_snippet}
    description: Optional[str] = ""
    role: Literal["application_claim", "proof", "contextual"]
    validation_requirements: Optional[ValidationRequirements] = None
    supports: List[SupportsItem] = []
    confidence: float = 0.0

class FieldRelationship(BaseModel):
    from_field_id: str
    to_field_id: str
    relationship: Literal["supports", "contradicts", "duplicates", "derives"]
    confidence: float
    reason: str

class SchemaProjectionItem(BaseModel):
    schema_field: str
    value: Optional[Any]
    derived_from: List[str] # List of field_ids
    confidence: float
    reasoning: str

class SchemaProjection(BaseModel):
    schema_name: str
    ordered_fields: List[SchemaProjectionItem]
    unmapped_fields: List[FieldEntity] = Field(default_factory=list)

class ValidationSummary(BaseModel):
    """
    Validation summary: derived metrics ONLY.
    No summary text, no extraction completeness logic.
    """
    total_schema_fields: int = 0
    validated_fields: int = 0
    errors: int = 0
    warnings: int = 0
    confidence_score: float = 1.0

class VerificationReport(BaseModel):
    """
    Canonical Response Model (Schema-Last)
    CENTRIC ON field_entities.
    """
    application_type: str
    documents: List[Dict[str, Any]]
    field_entities: List[FieldEntity]
    field_relationships: List[FieldRelationship]
    schema_projection: SchemaProjection
    validation_summary: ValidationSummary
    issues: List[ValidationIssue]
    metadata: Dict[str, Any] = {}

# Canonical Alias
UniversalExtractionResponse = VerificationReport
VerificationIssue = ValidationIssue

