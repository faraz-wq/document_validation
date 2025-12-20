from app.verification.schema import VerificationConfig, KeyDetailDefinition, ValidationRuleDefinition
from typing import Dict

VERIFICATION_REGISTRY: Dict[str, VerificationConfig] = {}

# 1. Integrated Certificate Configuration (Clean Slate)
INTEGRATED_CERTIFICATE_CONFIG = VerificationConfig(
    application_type="Integrated Certificate",
    key_details=[
        KeyDetailDefinition(
            field_path="applicant_name",
            display_name="Applicant Name",
            description="Full name of the person applying",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="fathers_name",
            display_name="Father's Name",
            description="Name of the applicant's father",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="community",
            display_name="Community/Caste",
            description="The caste or community claimed",
            valid_proof_documents=["Caste Certificate", "Affidavit"]
        ),
        KeyDetailDefinition(
            field_path="nativity",
            display_name="Nativity/Residence",
            description="Resident status verification",
            valid_proof_documents=["Caste Certificate", "Ration Card", "Application Form"]
        )
    ],
    rules=[
        ValidationRuleDefinition(
            rule_id="name_consistency",
            description="Applicant name must be consistent across all supporting documents",
            severity="error",
            rule_type="consistency",
            fields_involved=["applicant_name"]
        ),
        ValidationRuleDefinition(
            rule_id="mandatory_caste_proof",
            description="Community details must be backed by a government-issued Caste Certificate",
            severity="error",
            rule_type="proof_existence",
            fields_involved=["community"]
        )
    ]
)

# 2. Family Member Certificate Configuration
FAMILY_MEMBER_CONFIG = VerificationConfig(
    application_type="Family Member Certificate",
    key_details=[
        KeyDetailDefinition(
            field_path="applicant_name",
            display_name="Applicant Name",
            description="Name of the person applying for the certificate",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="deceased_details.deceased_name",
            display_name="Deceased Person Name",
            description="Name of the deceased member",
            valid_proof_documents=["Death Certificate", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="deceased_details.date_of_death",
            display_name="Date of Death",
            description="When the person passed away",
            valid_proof_documents=["Death Certificate"]
        ),
        KeyDetailDefinition(
            field_path="heirs_details",
            display_name="Heirs Details",
            description="List of all surviving family members",
            valid_proof_documents=["Application Form", "Ration Card"]
        )
    ],
    rules=[
        ValidationRuleDefinition(
            rule_id="name_consistency",
            description="Applicant name must be consistent across all supporting documents",
            severity="error",
            rule_type="consistency",
            fields_involved=["applicant_name"]
        ),
        ValidationRuleDefinition(
            rule_id="proof_of_relationship",
            description="Relationship proof must be provided for all heirs",
            severity="error",
            rule_type="proof_existence",
            fields_involved=["heirs_details"]
        )
    ]
)

def register_config(config: VerificationConfig):
    VERIFICATION_REGISTRY[config.application_type] = config

# Registration
register_config(INTEGRATED_CERTIFICATE_CONFIG)
register_config(FAMILY_MEMBER_CONFIG)

def get_verification_config(app_type: str) -> VerificationConfig:
    return VERIFICATION_REGISTRY.get(app_type)
