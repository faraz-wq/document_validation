"""
Certificate type specifications and field definitions
Defines required documents and summary fields for each certificate type
"""

from enum import Enum
from typing import List, Dict

class CertificateType(Enum):
    """Enumeration of supported certificate types"""
    INTEGRATED = "integrated"
    INCOME = "income"
    OBC = "obc"
    EWS = "ews"
    FAMILY_MEMBER = "family_member"

class CertificateSpecs:
    """Certificate specifications including required documents and summary fields"""

    SPECS: Dict[CertificateType, Dict] = {
        CertificateType.INTEGRATED: {
            "name": "Integrated Certificate",
            "description": "Community, Nativity, DOB Certificate",
            "required_documents": [
                "Application Form",
                "Caste Certificate",
                "SSC marks memo/DOB extract/TC",
                "Study Certificates",
                "Ration card/EPIC/Aadhaar",
                "Schedule I-IV"
            ],
            "summary_fields": [
                "Title of the document",
                "Name of the Applicant",
                "Father's Name",
                "Address",
                "Gender",
                "Age/DOB",
                "Phone Number",
                "Ration Card Number",
                "Community",
                "Nativity",
                "Family Income",
                "Issuer of the Document/Authority Signed",
                "Date of Issue"
            ]
        },

        CertificateType.INCOME: {
            "name": "Income Certificate",
            "description": "Income verification certificate",
            "required_documents": [
                "Application Form",
                "Ration card/EPIC/Aadhaar",
                "IT Returns/Pay Slips"
            ],
            "summary_fields": [
                "Title of the document",
                "Name of the Applicant",
                "Father's Name",
                "Address",
                "Gender",
                "Age/DOB",
                "Phone Number",
                "Ration Card Number",
                "Income Details - Income on Lands",
                "Income Details - Income on Business",
                "Income Details - Income on Buildings",
                "Income Details - Income on Labour",
                "Income Details - Salary of both Wife & Husband",
                "Income Details - Income on Other Sources",
                "Income Details - Total Income",
                "Issuer of the Document/Authority Signed",
                "Date of Issue"
            ]
        },

        CertificateType.OBC: {
            "name": "OBC Certificate",
            "description": "Other Backward Classes Certificate",
            "required_documents": [
                "Application Form",
                "Ration card/EPIC/Aadhaar",
                "Property particulars",
                "Employment particulars/IT returns"
            ],
            "summary_fields": [
                "Title of the document",
                "Name of the Applicant",
                "Father's Name",
                "Address",
                "Gender",
                "Age/DOB",
                "Phone Number",
                "Caste",
                "Sub-Caste",
                "Family Income",
                "Issuer of the Document/Authority Signed",
                "Date of Issue"
            ]
        },

        CertificateType.EWS: {
            "name": "EWS Certificate",
            "description": "Economically Weaker Sections Certificate",
            "required_documents": [
                "Application Form",
                "Ration card/EPIC/Aadhaar",
                "IT Returns/Pay slips",
                "Affidavit"
            ],
            "summary_fields": [
                "Title of the document",
                "Name of the Applicant",
                "Father's Name",
                "Address",
                "Gender",
                "Age/DOB",
                "Phone Number",
                "Ration Card Number",
                "Community",
                "Assets Details - Agriculture Land",
                "Assets Details - Residential Flat",
                "Assets Details - Residential Plot & Municipality",
                "Gross Annual Income",
                "Issuer of the Document/Authority Signed",
                "Date of Issue"
            ]
        },

        CertificateType.FAMILY_MEMBER: {
            "name": "Family Member Certificate",
            "description": "Family Member Certificate for deceased HOF",
            "required_documents": [
                "Application Form",
                "Notarized affidavit",
                "Relationship documents",
                "Death Certificate/FIR"
            ],
            "summary_fields": [
                "Title of the document",
                "Name of the Applicant",
                "Father's Name",
                "Address",
                "Gender",
                "Age/DOB",
                "Phone Number",
                "Deceased Details - Deceased HOF's Name",
                "Deceased Details - Father/Husband Name",
                "Deceased Details - Date of Death",
                "Deceased Details - Reason for Death",
                "Deceased Details - Occupation",
                "Deceased Details - Aadhaar Number",
                "Deceased Details - Place of Death",
                "Details of Family Members of the Deceased HOF - Name",
                "Details of Family Members of the Deceased HOF - Gender",
                "Details of Family Members of the Deceased HOF - Age",
                "Details of Family Members of the Deceased HOF - Relationship with HOF",
                "Issuer of the Document/Authority Signed",
                "Date of Issue"
            ]
        }
    }

    @classmethod
    def get_certificate_types(cls) -> List[str]:
        """Get list of all certificate type names"""
        return [cert.value for cert in CertificateType]

    @classmethod
    def get_spec(cls, cert_type: CertificateType) -> Dict:
        """Get specification for a specific certificate type"""
        return cls.SPECS.get(cert_type, {})

    @classmethod
    def get_summary_fields(cls, cert_type: CertificateType) -> List[str]:
        """Get summary fields for a specific certificate type"""
        spec = cls.get_spec(cert_type)
        return spec.get("summary_fields", [])

    @classmethod
    def get_required_documents(cls, cert_type: CertificateType) -> List[str]:
        """Get required documents for a specific certificate type"""
        spec = cls.get_spec(cert_type)
        return spec.get("required_documents", [])

    @classmethod
    def from_string(cls, type_str: str) -> CertificateType:
        """Convert string to CertificateType enum"""
        type_str = type_str.lower().strip()
        for cert_type in CertificateType:
            if cert_type.value == type_str:
                return cert_type
        raise ValueError(f"Unknown certificate type: {type_str}")
