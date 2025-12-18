from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# ==============================================================================
# 1. COMMON NESTED MODELS (Reusable across all services for consistency)
# ==============================================================================

class SourceDocument(BaseModel):
    """Maps extracted data back to the source file for traceability."""
    document_title: str = Field(
        description="The primary title or type of the document (e.g., 'Application Form', 'Aadhaar Card')."
    )
    filename: str = Field(
        description="The original filename of the document (e.g., 'caste.pdf')."
    )
    page_numbers: List[int] = Field(
        default_factory=list,
        description="List of page numbers (1-indexed) where this document type was found."
    )

class BoundingBox(BaseModel):
    """Bounding box coordinates for a field in a document."""
    filename: str = Field(description="The filename where this data was found")
    document_title: Optional[str] = Field(default=None, description="The inferred title or type of the document")
    page: int = Field(description="Page number (1-indexed)")
    coordinates: List[float] = Field(
        description="Normalized bounding box coordinates [y_min, x_min, y_max, x_max] scaled to 1000x1000"
    )

class ApplicantCommon(BaseModel):
    """Common details required for most applications."""
    applicant_name: Optional[str] = None
    fathers_name: Optional[str] = None
    address: Optional[str] = Field(default=None, description="Consolidated full address.")
    gender: Optional[str] = None
    age_dob: Optional[str] = Field(default=None, description="Age or Date of Birth (DD/MM/YYYY).")
    phone_number: Optional[str] = None
    
# ==============================================================================
# 2. UNIQUE NESTED MODELS (Service-specific data structures)
# ==============================================================================

# --- Unique to Income Certificate (Service 2) ---
class IncomeDetails(BaseModel):
    """Specific breakdown of income sources for the Income Certificate."""
    income_on_lands: Optional[str] = None
    income_on_business: Optional[str] = None
    income_on_buildings: Optional[str] = None
    income_on_labour: Optional[str] = None
    salary_wife_husband: Optional[str] = Field(default=None, description="Consolidated salary of both wife and husband.")
    income_on_other_sources: Optional[str] = None
    total_gross_income: Optional[str] = Field(default=None, description="The final calculated total annual income.")

# --- Unique to EWS Certificate (Service 4) ---
class AssetDetailsEWS(BaseModel):
    """Specific asset breakdown for the EWS Certificate."""
    agriculture_land: Optional[str] = Field(default=None, description="Size/value of agricultural land.")
    residential_flat: Optional[str] = Field(default=None, description="Size/value of residential flat.")
    residential_plot_municipality: Optional[str] = Field(default=None, description="Size/value of residential plot/municipality plot.")
    gross_annual_income: Optional[str] = None

# --- Unique to Family Member Certificate (Service 5) ---
class FamilyMember(BaseModel):
    """Details of a single family member of the deceased HOF."""
    name: str
    gender: str
    age: Optional[int] = None
    relationship_with_hof: str

class DeceasedHOFDetails(BaseModel):
    """Details about the deceased Head of Family for the Family Member Certificate."""
    deceased_hof_name: str
    father_husband_name: str
    date_of_death: str
    reason_for_death: Optional[str] = None
    occupation: Optional[str] = None
    aadhaar_number: Optional[str] = None
    place_of_death: Optional[str] = None


# ==============================================================================
# 3. FINAL SERVICE SUMMARY SCHEMAS (5 distinct models)
# ==============================================================================

# --- 1. Integrated Certificate (Community, Nativity, DOB) ---
class IntegratedCertificateSummary(ApplicantCommon):
    """Schema for Community, Nativity, and DOB Certificate."""
    ration_card_number: Optional[str] = None
    community: Optional[str] = None
    nativity: Optional[str] = None
    family_income: Optional[str] = None
    key_details: Optional[str] = None
    issuer_authority: Optional[str] = None
    date_of_issue: Optional[str] = None
    source_documents: List[SourceDocument]
    citations: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of field names to their source (filename and page number). Use dot notation for nested fields (e.g. 'applicant_name', 'income_details.total_gross_income')."
    )
    bounding_boxes: Dict[str, List[BoundingBox]] = Field(
        default_factory=dict,
        description="Map of field names to a list of their bounding box coordinates (one for each occurrence). Use dot notation for nested fields."
    )
    errors: Optional[List[Any]] = Field(
        default_factory=list,
        alias="_errors",
        description="List of extraction errors or missing fields."
    )
    validation_summary: Optional[str] = Field(
        default=None,
        description="Natural language summary of extraction discrepancies."
    )

# --- 2. Income Certificate ---
class IncomeCertificateSummary(ApplicantCommon):
    """Schema for Income Certificate."""
    ration_card_number: Optional[str] = None
    key_details: Optional[str] = None
    income_details: IncomeDetails = Field(description="Detailed breakdown of all income sources.")
    issuer_authority: Optional[str] = None
    date_of_issue: Optional[str] = None
    source_documents: List[SourceDocument]
    citations: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of field names to their source (filename and page number). Use dot notation for nested fields."
    )
    bounding_boxes: Dict[str, List[BoundingBox]] = Field(
        default_factory=dict,
        description="Map of field names to a list of their bounding box coordinates (one for each occurrence). Use dot notation for nested fields."
    )
    errors: Optional[List[Any]] = Field(
        default_factory=list,
        alias="_errors",
        description="List of extraction errors or missing fields."
    )
    validation_summary: Optional[str] = Field(
        default=None,
        description="Natural language summary of extraction discrepancies."
    )

# --- 3. OBC Certificate ---
class OBCCertificateSummary(ApplicantCommon):
    """Schema for OBC Certificate."""
    caste: Optional[str] = None
    sub_caste: Optional[str] = None
    family_income: Optional[str] = None
    key_details: Optional[str] = None
    issuer_authority: Optional[str] = None
    date_of_issue: Optional[str] = None
    source_documents: List[SourceDocument]
    citations: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of field names to their source (filename and page number). Use dot notation for nested fields."
    )
    bounding_boxes: Dict[str, List[BoundingBox]] = Field(
        default_factory=dict,
        description="Map of field names to a list of their bounding box coordinates (one for each occurrence). Use dot notation for nested fields."
    )
    errors: Optional[List[Any]] = Field(
        default_factory=list,
        alias="_errors",
        description="List of extraction errors or missing fields."
    )
    validation_summary: Optional[str] = Field(
        default=None,
        description="Natural language summary of extraction discrepancies."
    )

# --- 4. EWS Income & Asset Certificate ---
class EWSCertificateSummary(ApplicantCommon):
    """Schema for EWS Income & Asset Certificate."""
    ration_card_number: Optional[str] = None
    community: Optional[str] = None
    key_details: Optional[str] = None
    asset_details: AssetDetailsEWS = Field(description="Breakdown of specific assets and gross income.")
    issuer_authority: Optional[str] = None
    date_of_issue: Optional[str] = None
    source_documents: List[SourceDocument]
    citations: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of field names to their source (filename and page number). Use dot notation for nested fields."
    )
    bounding_boxes: Dict[str, List[BoundingBox]] = Field(
        default_factory=dict,
        description="Map of field names to a list of their bounding box coordinates (one for each occurrence). Use dot notation for nested fields."
    )
    errors: Optional[List[Any]] = Field(
        default_factory=list,
        alias="_errors",
        description="List of extraction errors or missing fields."
    )
    validation_summary: Optional[str] = Field(
        default=None,
        description="Natural language summary of extraction discrepancies."
    )

# --- 5. Family Member Certificate ---
class FamilyMemberCertificateSummary(ApplicantCommon):
    """Schema for Family Member Certificate."""
    deceased_details: DeceasedHOFDetails
    family_members_of_hof: List[FamilyMember] = Field(description="List of living family members and their relationship to the HOF.")
    key_details: Optional[str] = None
    issuer_authority: Optional[str] = None
    date_of_issue: Optional[str] = None
    source_documents: List[SourceDocument]
    citations: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of field names to their source (filename and page number). Use dot notation for nested fields."
    )
    bounding_boxes: Dict[str, List[BoundingBox]] = Field(
        default_factory=dict,
        description="Map of field names to a list of their bounding box coordinates (one for each occurrence). Use dot notation for nested fields."
    )
    errors: Optional[List[Any]] = Field(
        default_factory=list,
        alias="_errors",
        description="List of extraction errors or missing fields."
    )
    validation_summary: Optional[str] = Field(
        default=None,
        description="Natural language summary of extraction discrepancies."
    )
