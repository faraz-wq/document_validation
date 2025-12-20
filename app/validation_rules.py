from typing import List, Dict, Set, Callable, Any, Optional
from pydantic import BaseModel, Field
from dataclasses import dataclass


@dataclass
class ValidationRuleSet:
    """
    Defines validation rules for a specific application type.
    This is the configuration object that makes validation pluggable.
    """
    application_type: str
    required_fields: List[str]  # Dot notation paths (e.g., "applicant_name", "income_details.total_gross_income")
    required_documents: List[str]  # Document types that must be present (e.g., "Aadhaar Card", "Affidavit")
    critical_fields: List[str]  # Fields that must be consistent across all documents
    fuzzy_match_fields: List[str]  # Fields where fuzzy matching is acceptable (e.g., names)
    proof_requirements: Optional[Dict[str, List[str]]] = None # Maps field paths to required doc titles (e.g., {"applicant_name": ["Aadhaar Card"]})
    array_proof_mappings: Optional[Dict[str, str]] = None  # Maps array paths to their proof field (e.g., "family_members_of_hof": "aadhaar")
    custom_validators: Optional[List[Callable]] = None  # Custom validation functions


# Registry of validation rules keyed by application_type
VALIDATION_RULES: Dict[str, ValidationRuleSet] = {}


def register_validation_rules(rule_set: ValidationRuleSet):
    """Register a new validation rule set for an application type."""
    VALIDATION_RULES[rule_set.application_type] = rule_set


def get_validation_rules(application_type: str) -> Optional[ValidationRuleSet]:
    """Retrieve validation rules for a given application type."""
    return VALIDATION_RULES.get(application_type)


# ==============================================================================
# PREDEFINED RULE SETS
# ==============================================================================

# Family Member Certificate Rules
FAMILY_MEMBER_CERTIFICATE_RULES = ValidationRuleSet(
    application_type="Family Member Certificate",
    required_fields=[
        "applicant_name",
        "deceased_details.deceased_hof_name",
        "deceased_details.father_husband_name",
        "deceased_details.date_of_death",
        "family_members_of_hof"
    ],
    required_documents=[
        "Death Certificate",
        "Aadhaar Card",
        "Application Form"
    ],
    critical_fields=[
        "deceased_details.deceased_hof_name",
        "deceased_details.date_of_death",
        "deceased_details.aadhaar_number"
    ],
    fuzzy_match_fields=[
        "applicant_name",
        "deceased_details.deceased_hof_name",
        "deceased_details.father_husband_name"
    ],
    array_proof_mappings={
        "family_members_of_hof": "name"  # Each family member should have a name
    }
)

# Income Certificate Rules
INCOME_CERTIFICATE_RULES = ValidationRuleSet(
    application_type="Income Certificate",
    required_fields=[
        "applicant_name",
        "fathers_name",
        "address",
        "income_details.total_gross_income"
    ],
    required_documents=[
        "Application Form",
        "Aadhaar Card",
        "Income Proof"
    ],
    critical_fields=[
        "applicant_name",
        "income_details.total_gross_income"
    ],
    fuzzy_match_fields=[
        "applicant_name",
        "fathers_name"
    ]
)

# OBC Certificate Rules
OBC_CERTIFICATE_RULES = ValidationRuleSet(
    application_type="OBC Certificate",
    required_fields=[
        "applicant_name",
        "fathers_name",
        "caste",
        "address"
    ],
    required_documents=[
        "Application Form",
        "Aadhaar Card",
        "Caste Certificate"
    ],
    critical_fields=[
        "applicant_name",
        "caste"
    ],
    fuzzy_match_fields=[
        "applicant_name",
        "fathers_name"
    ]
)

# EWS Certificate Rules
EWS_CERTIFICATE_RULES = ValidationRuleSet(
    application_type="EWS Certificate",
    required_fields=[
        "applicant_name",
        "fathers_name",
        "address",
        "asset_details.gross_annual_income"
    ],
    required_documents=[
        "Application Form",
        "Aadhaar Card",
        "Income Proof"
    ],
    critical_fields=[
        "applicant_name",
        "asset_details.gross_annual_income"
    ],
    fuzzy_match_fields=[
        "applicant_name",
        "fathers_name"
    ]
)

# Integrated Certificate Rules
INTEGRATED_CERTIFICATE_RULES = ValidationRuleSet(
    application_type="Integrated Certificate",
    required_fields=[
        "applicant_name",
        "fathers_name",
        "address",
        "community"
    ],
    required_documents=[
        "Application Form",
        "Aadhaar Card",
        "Caste Certificate"
    ],
    critical_fields=[
        "applicant_name",
        "community"
    ],
    fuzzy_match_fields=[
        "applicant_name",
        "fathers_name"
    ],
    proof_requirements={
        "applicant_name": ["Aadhaar Card", "Application Form"],
        "community": ["Caste Certificate"],
        "nativity": ["Caste Certificate"]
    }
)

# Register all predefined rules
register_validation_rules(FAMILY_MEMBER_CERTIFICATE_RULES)
register_validation_rules(INCOME_CERTIFICATE_RULES)
register_validation_rules(OBC_CERTIFICATE_RULES)
register_validation_rules(EWS_CERTIFICATE_RULES)
register_validation_rules(INTEGRATED_CERTIFICATE_RULES)
