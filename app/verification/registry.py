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
            valid_proof_documents=["Aadhaar Card", "Application Form", "Ration Card"]
        ),
        KeyDetailDefinition(
            field_path="applicant_aadhaar",
            display_name="Applicant Aadhaar Number",
            description="Aadhaar card number of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="fathers_name",
            display_name="Father's Name",
            description="Name of the applicant's father",
            valid_proof_documents=["Aadhaar Card", "Application Form", "Ration Card"]
        ),
        KeyDetailDefinition(
            field_path="mothers_name",
            display_name="Mother's Name",
            description="Name of the applicant's mother",
            valid_proof_documents=["Application Form", "Ration Card"]
        ),
        KeyDetailDefinition(
            field_path="date_of_birth",
            display_name="Date of Birth",
            description="Date of birth of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="gender",
            display_name="Gender",
            description="Gender of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="address",
            display_name="Address",
            description="Residential address of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form", "Ration Card"]
        ),
        KeyDetailDefinition(
            field_path="phone_number",
            display_name="Phone Number",
            description="Contact phone number",
            valid_proof_documents=["Application Form"]
        ),
        KeyDetailDefinition(
            field_path="ration_card_number",
            display_name="Ration Card Number",
            description="Ration card number for the family",
            valid_proof_documents=["Ration Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="community",
            display_name="Community/Caste",
            description="The caste or community claimed",
            valid_proof_documents=["Caste Certificate", "Affidavit", "Study Certificate"]
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
            rule_id="fathers_name_consistency",
            description="Father's name must be consistent across all supporting documents",
            severity="error",
            rule_type="consistency",
            fields_involved=["fathers_name"]
        ),
        ValidationRuleDefinition(
            rule_id="mandatory_caste_proof",
            description="Community details must be backed by a government-issued Caste Certificate",
            severity="error",
            rule_type="proof_existence",
            fields_involved=["community"]
        ),
        ValidationRuleDefinition(
            rule_id="aadhaar_format",
            description="Aadhaar number must be in valid format (12 digits)",
            severity="warning",
            rule_type="format",
            fields_involved=["applicant_aadhaar"]
        ),
        ValidationRuleDefinition(
            rule_id="address_consistency",
            description="Address should be consistent across Aadhaar, Application Form, and Ration Card",
            severity="warning",
            rule_type="consistency",
            fields_involved=["address"]
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
            field_path="applicant_aadhaar",
            display_name="Applicant Aadhaar Number",
            description="Aadhaar card number of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="fathers_name",
            display_name="Father's Name",
            description="Father's / Husband's name",
            valid_proof_documents=["Aadhaar Card", "Application Form", "Income Certificate"]
        ),
        KeyDetailDefinition(
            field_path="date_of_birth",
            display_name="Date of Birth",
            description="Date of birth of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="gender",
            display_name="Gender",
            description="Gender of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="address",
            display_name="Address",
            description="Residential address of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="phone_number",
            display_name="Phone Number",
            description="Contact phone number",
            valid_proof_documents=["Application Form"]
        ),
        KeyDetailDefinition(
            field_path="occupation",
            display_name="Occupation",
            description="Occupation or profession of the applicant",
            valid_proof_documents=["Application Form", "Income Certificate"]
        ),
        KeyDetailDefinition(
            field_path="income_details.total_gross_income",
            display_name="Annual Family Income",
            description="Total gross annual income from all sources",
            valid_proof_documents=["Income Certificate", "Salary Slip", "IT Returns"]
        ),
        KeyDetailDefinition(
            field_path="income_details.income_sources",
            display_name="Income Sources",
            description="List of all income sources (salary, business, agriculture, etc.)",
            valid_proof_documents=["Income Certificate", "Salary Slip", "IT Returns", "Application Form"]
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
            rule_id="fathers_name_consistency",
            description="Father's/Husband's name must be consistent across documents",
            severity="error",
            rule_type="consistency",
            fields_involved=["fathers_name"]
        ),
        ValidationRuleDefinition(
            rule_id="income_proof_mandatory",
            description="Income must be supported by either a Salary Slip, IT Return or a certified declaration",
            severity="warning",
            rule_type="proof_existence",
            fields_involved=["income_details.total_gross_income"]
        ),
        ValidationRuleDefinition(
            rule_id="aadhaar_format",
            description="Aadhaar number must be in valid format (12 digits)",
            severity="warning",
            rule_type="format",
            fields_involved=["applicant_aadhaar"]
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
            field_path="applicant_aadhaar",
            display_name="Applicant Aadhaar Number",
            description="Aadhaar card number of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="fathers_name",
            display_name="Father's Name",
            description="Father's or husband's name of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="date_of_birth",
            display_name="Date of Birth",
            description="Date of birth of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="address",
            display_name="Address",
            description="Residential address of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="phone_number",
            display_name="Phone Number",
            description="Contact phone number",
            valid_proof_documents=["Application Form"]
        ),
        KeyDetailDefinition(
            field_path="asset_details.gross_annual_income",
            display_name="Gross Annual Income",
            description="Total gross annual income of the family",
            valid_proof_documents=["Income Certificate", "Salary Slip", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="asset_details.property_details",
            display_name="Property Details",
            description="Details of agricultural land, residential property, and other assets",
            valid_proof_documents=["Property Documents", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="community",
            display_name="Community",
            description="Must not belong to SC/ST/OBC category for EWS",
            valid_proof_documents=["Caste Certificate", "Affidavit", "Application Form"]
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
            rule_id="fathers_name_consistency",
            description="Father's/Husband's name must be consistent across documents",
            severity="error",
            rule_type="consistency",
            fields_involved=["fathers_name"]
        ),
        ValidationRuleDefinition(
            rule_id="ews_income_limit",
            description="Gross annual income must be below 8 Lakhs for EWS eligibility",
            severity="error",
            rule_type="logic",
            fields_involved=["asset_details.gross_annual_income"]
        ),
        ValidationRuleDefinition(
            rule_id="ews_community_check",
            description="Applicant must not belong to SC/ST/OBC categories for EWS eligibility",
            severity="error",
            rule_type="logic",
            fields_involved=["community"]
        ),
        ValidationRuleDefinition(
            rule_id="aadhaar_format",
            description="Aadhaar number must be in valid format (12 digits)",
            severity="warning",
            rule_type="format",
            fields_involved=["applicant_aadhaar"]
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
            field_path="applicant_aadhaar",
            display_name="Applicant Aadhaar Number",
            description="Aadhaar card number of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="applicant_dob",
            display_name="Applicant Date of Birth",
            description="Date of birth of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="applicant_address",
            display_name="Applicant Address",
            description="Residential address of the applicant",
            valid_proof_documents=["Aadhaar Card", "Application Form"]
        ),
        KeyDetailDefinition(
            field_path="applicant_phone",
            display_name="Applicant Phone Number",
            description="Contact phone number of the applicant",
            valid_proof_documents=["Application Form"]
        ),
        KeyDetailDefinition(
            field_path="deceased_details.deceased_hof_name",
            display_name="Deceased Person Name",
            description="Name of the deceased member",
            valid_proof_documents=["Death Certificate", "Application Form", "Affidavit"]
        ),
        KeyDetailDefinition(
            field_path="deceased_details.date_of_death",
            display_name="Date of Death",
            description="When the person passed away",
            valid_proof_documents=["Death Certificate", "Application Form", "Affidavit"]
        ),
        KeyDetailDefinition(
            field_path="deceased_details.deceased_father_husband_name",
            display_name="Deceased's Father/Husband Name",
            description="Father's or husband's name of the deceased person",
            valid_proof_documents=["Death Certificate", "Application Form", "Affidavit"]
        ),
        KeyDetailDefinition(
            field_path="deceased_details.deceased_aadhaar",
            display_name="Deceased's Aadhaar Number",
            description="Aadhaar card number of the deceased person",
            valid_proof_documents=["Aadhaar Card", "Death Certificate"]
        ),
        KeyDetailDefinition(
            field_path="family_members",
            display_name="Family Members List",
            description="List of all family members with their details (name, age, gender, relationship, aadhaar)",
            valid_proof_documents=["Application Form", "Aadhaar Card", "Affidavit"]
        ),
        KeyDetailDefinition(
            field_path="relationship_to_deceased",
            display_name="Applicant's Relationship to Deceased",
            description="How the applicant is related to the deceased person",
            valid_proof_documents=["Application Form", "Affidavit"]
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
        ),
        ValidationRuleDefinition(
            rule_id="deceased_name_consistency",
            description="Deceased person's name must be consistent across Death Certificate, Application Form, and Affidavit",
            severity="error",
            rule_type="consistency",
            fields_involved=["deceased_details.deceased_hof_name"]
        ),
        ValidationRuleDefinition(
            rule_id="aadhaar_format",
            description="Aadhaar numbers must be in valid format (12 digits)",
            severity="warning",
            rule_type="format",
            fields_involved=["applicant_aadhaar", "deceased_details.deceased_aadhaar"]
        ),
        ValidationRuleDefinition(
            rule_id="family_member_proof",
            description="Family members listed should be verified against supporting Aadhaar cards",
            severity="warning",
            rule_type="proof_existence",
            fields_involved=["family_members"]
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
