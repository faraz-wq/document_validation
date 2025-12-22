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

# 2. Income Certificate Configuration
INCOME_CERTIFICATE_CONFIG = VerificationConfig(
    application_type="Income Certificate",
    key_details=[
        KeyDetailDefinition(
            field_path="applicant_name",
            display_name="Applicant Name",
            description="Full name of the person applying for Income Certificate",
            valid_proof_documents=["Aadhaar Card", "Application Form", "Income Certificate"]
        ),
        KeyDetailDefinition(
            field_path="fathers_name",
            display_name="Father's Name",
            description="Father's / Husband's name",
            valid_proof_documents=["Aadhaar Card", "Application Form", "Income Certificate"]
        ),
        KeyDetailDefinition(
            field_path="income_details.total_gross_income",
            display_name="Annual Family Income",
            description="Total gross annual income from all sources",
            valid_proof_documents=["Income Certificate", "Salary Slip", "IT Returns"]
        )
    ],
    rules=[
        ValidationRuleDefinition(
            rule_id="name_consistency",
            description="Name must match exactly across ID proofs and application form",
            severity="error",
            rule_type="consistency",
            fields_involved=["applicant_name"]
        ),
        ValidationRuleDefinition(
            rule_id="income_proof_mandatory",
            description="Income must be supported by either a Salary Slip, IT Return or a certified declaration",
            severity="warning",
            rule_type="proof_existence",
            fields_involved=["income_details.total_gross_income"]
        )
    ]
)

# 3. EWS Certificate Configuration
EWS_CERTIFICATE_CONFIG = VerificationConfig(
    application_type="EWS Certificate",
    key_details=[
        KeyDetailDefinition(
            field_path="applicant_name",
            display_name="Applicant Name",
            description="Full name of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="asset_details.gross_annual_income",
            display_name="Gross Annual Income",
            description="Total gross annual income of the family",
            valid_proof_documents=["Income Certificate", "Salary Slip"]
        ),
        KeyDetailDefinition(
            field_path="community",
            display_name="Community",
            description="Must not belong to SC/ST/OBC category for EWS",
            valid_proof_documents=["Caste Certificate", "Affidavit"]
        )
    ],
    rules=[
        ValidationRuleDefinition(
            rule_id="name_consistency",
            description="Applicant name must be consistent across all documents",
            severity="error",
            rule_type="consistency",
            fields_involved=["applicant_name"]
        ),
        ValidationRuleDefinition(
            rule_id="ews_income_limit",
            description="Gross annual income must be below 8 Lakhs for EWS eligibility",
            severity="error",
            rule_type="logic",
            fields_involved=["asset_details.gross_annual_income"]
        )
    ]
)

# 4. Family Member Certificate Configuration
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
            field_path="deceased_details.deceased_hof_name",
            display_name="Deceased Person Name",
            description="Name of the deceased member",
            valid_proof_documents=["Death Certificate", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="deceased_details.date_of_death",
            display_name="Date of Death",
            description="When the person passed away",
            valid_proof_documents=["Death Certificate"]
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
            rule_id="mandatory_death_proof",
            description="Death details must be backed by a government-issued Death Certificate",
            severity="error",
            rule_type="proof_existence",
            fields_involved=["deceased_details.date_of_death"]
        )
    ]
)

def register_config(config: VerificationConfig):
    VERIFICATION_REGISTRY[config.application_type] = config

# Registration
register_config(INTEGRATED_CERTIFICATE_CONFIG)
register_config(INCOME_CERTIFICATE_CONFIG)
register_config(EWS_CERTIFICATE_CONFIG)
register_config(FAMILY_MEMBER_CONFIG)

def get_verification_config(app_type: str) -> VerificationConfig:
    return VERIFICATION_REGISTRY.get(app_type)
