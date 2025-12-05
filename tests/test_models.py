import pytest
from pydantic import ValidationError

from app.models import (
    SourceDocument,
    BoundingBox,
    ApplicantCommon,
    IncomeDetails,
    AssetDetailsEWS,
    FamilyMember,
    DeceasedHOFDetails,
    IntegratedCertificateSummary,
    IncomeCertificateSummary,
    OBCCertificateSummary,
    EWSCertificateSummary,
    FamilyMemberCertificateSummary
)


class TestModels:
    """Test cases for the Pydantic models in app.models"""

    def test_source_document_model(self):
        """Test SourceDocument model"""
        source_doc = SourceDocument(
            document_title="Income Certificate",
            filename="test.pdf"
        )

        assert source_doc.filename == "test.pdf"
        assert source_doc.document_title == "Income Certificate"

    def test_source_document_model_validation(self):
        """Test SourceDocument model validation"""
        # Should work with required fields
        source_doc = SourceDocument(
            document_title="Income Certificate",
            filename="test.pdf"
        )
        assert source_doc.document_title == "Income Certificate"

    def test_bounding_box_model(self):
        """Test BoundingBox model"""
        bbox = BoundingBox(
            filename="test.pdf",
            page=1,
            coordinates=[0, 0, 100, 100]
        )

        assert bbox.filename == "test.pdf"
        assert bbox.page == 1
        assert bbox.coordinates == [0, 0, 100, 100]

    def test_bounding_box_model_validation(self):
        """Test BoundingBox model validation"""
        # Valid coordinates
        bbox = BoundingBox(
            filename="test.pdf",
            page=1,
            coordinates=[100, 200, 300, 400]
        )
        assert len(bbox.coordinates) == 4

    def test_applicant_common_model(self):
        """Test ApplicantCommon model"""
        applicant = ApplicantCommon(
            applicant_name="John Doe",
            fathers_name="Jane Doe",
            address="123 Main St",
            gender="Male",
            age_dob="01/01/1990",
            phone_number="1234567890"
        )

        assert applicant.applicant_name == "John Doe"
        assert applicant.fathers_name == "Jane Doe"
        assert applicant.address == "123 Main St"
        assert applicant.gender == "Male"
        assert applicant.age_dob == "01/01/1990"
        assert applicant.phone_number == "1234567890"

    def test_applicant_common_model_optional_fields(self):
        """Test ApplicantCommon model with optional fields"""
        # Test with minimal data
        applicant = ApplicantCommon(applicant_name="John Doe")
        assert applicant.applicant_name == "John Doe"
        assert applicant.fathers_name is None
        assert applicant.address is None

    def test_income_details_model(self):
        """Test IncomeDetails model"""
        income_details = IncomeDetails(
            income_on_lands="10000",
            income_on_business="20000",
            income_on_buildings="5000",
            income_on_labour="15000",
            salary_wife_husband="30000",
            income_on_other_sources="5000",
            total_gross_income="85000"
        )

        assert income_details.income_on_lands == "10000"
        assert income_details.total_gross_income == "85000"

    def test_asset_details_ews_model(self):
        """Test AssetDetailsEWS model"""
        asset_details = AssetDetailsEWS(
            agriculture_land="5 acres",
            residential_flat="1000 sq ft",
            residential_plot_municipality="2000 sq ft",
            gross_annual_income="100000"
        )

        assert asset_details.agriculture_land == "5 acres"
        assert asset_details.gross_annual_income == "100000"

    def test_family_member_model(self):
        """Test FamilyMember model"""
        family_member = FamilyMember(
            name="John Doe",
            gender="Male",
            age=30,
            relationship_with_hof="Son"
        )

        assert family_member.name == "John Doe"
        assert family_member.gender == "Male"
        assert family_member.age == 30
        assert family_member.relationship_with_hof == "Son"

    def test_family_member_model_optional_age(self):
        """Test FamilyMember model with optional age"""
        family_member = FamilyMember(
            name="John Doe",
            gender="Male",
            relationship_with_hof="Son"
        )

        assert family_member.name == "John Doe"
        assert family_member.age is None

    def test_deceased_hof_details_model(self):
        """Test DeceasedHOFDetails model"""
        deceased_details = DeceasedHOFDetails(
            deceased_hof_name="John Doe",
            father_husband_name="Jane Doe",
            date_of_death="01/01/2020",
            reason_for_death="Natural",
            occupation="Engineer",
            aadhaar_number="123456789012",
            place_of_death="City Hospital"
        )

        assert deceased_details.deceased_hof_name == "John Doe"
        assert deceased_details.reason_for_death == "Natural"

    def test_integrated_certificate_summary_model(self):
        """Test IntegratedCertificateSummary model"""
        summary = IntegratedCertificateSummary(
            applicant_name="John Doe",
            fathers_name="Jane Doe",
            ration_card_number="RC123",
            community="General",
            nativity="Indian",
            family_income="50000",
            key_details="Key details",
            issuer_authority="Authority",
            date_of_issue="01/01/2023",
            source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
            citations={},
            bounding_boxes={}
        )

        assert summary.applicant_name == "John Doe"
        assert len(summary.source_documents) == 1

    def test_income_certificate_summary_model(self):
        """Test IncomeCertificateSummary model"""
        income_details = IncomeDetails(total_gross_income="50000")
        summary = IncomeCertificateSummary(
            applicant_name="John Doe",
            fathers_name="Jane Doe",
            ration_card_number="RC123",
            key_details="Key details",
            income_details=income_details,
            issuer_authority="Authority",
            date_of_issue="01/01/2023",
            source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
            citations={},
            bounding_boxes={}
        )

        assert summary.applicant_name == "John Doe"
        assert summary.income_details.total_gross_income == "50000"

    def test_obb_certificate_summary_model(self):
        """Test OBCCertificateSummary model"""
        summary = OBCCertificateSummary(
            applicant_name="John Doe",
            fathers_name="Jane Doe",
            caste="OBC",
            sub_caste="SubCaste",
            family_income="50000",
            key_details="Key details",
            issuer_authority="Authority",
            date_of_issue="01/01/2023",
            source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
            citations={},
            bounding_boxes={}
        )

        assert summary.applicant_name == "John Doe"
        assert summary.caste == "OBC"

    def test_ews_certificate_summary_model(self):
        """Test EWSCertificateSummary model"""
        asset_details = AssetDetailsEWS(gross_annual_income="30000")
        summary = EWSCertificateSummary(
            applicant_name="John Doe",
            fathers_name="Jane Doe",
            ration_card_number="RC123",
            community="EWS",
            key_details="Key details",
            asset_details=asset_details,
            issuer_authority="Authority",
            date_of_issue="01/01/2023",
            source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
            citations={},
            bounding_boxes={}
        )

        assert summary.applicant_name == "John Doe"
        assert summary.asset_details.gross_annual_income == "30000"

    def test_family_member_certificate_summary_model(self):
        """Test FamilyMemberCertificateSummary model"""
        deceased_details = DeceasedHOFDetails(
            deceased_hof_name="John Doe",
            father_husband_name="Jane Doe",
            date_of_death="01/01/2020"
        )
        family_member = FamilyMember(
            name="Jane Smith",
            gender="Female",
            relationship_with_hof="Daughter"
        )
        
        summary = FamilyMemberCertificateSummary(
            applicant_name="Jane Smith",
            fathers_name="John Smith",
            deceased_details=deceased_details,
            family_members_of_hof=[family_member],
            key_details="Key details",
            issuer_authority="Authority",
            date_of_issue="01/01/2023",
            source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
            citations={},
            bounding_boxes={}
        )

        assert summary.applicant_name == "Jane Smith"
        assert summary.deceased_details.deceased_hof_name == "John Doe"
        assert len(summary.family_members_of_hof) == 1

    def test_source_document_model_missing_required_fields(self):
        """Test SourceDocument model with missing required fields"""
        with pytest.raises(ValidationError):
            SourceDocument()  # No required fields provided

    def test_bounding_box_model_invalid_coordinates(self):
        """Test BoundingBox model with invalid coordinates"""
        # Should work with 4 coordinates
        bbox = BoundingBox(
            filename="test.pdf",
            page=1,
            coordinates=[100, 200, 300, 400]
        )
        assert len(bbox.coordinates) == 4

    def test_applicant_common_model_extra_fields(self):
        """Test that ApplicantCommon handles extra fields appropriately"""
        # Model should ignore extra fields by default
        applicant = ApplicantCommon(
            applicant_name="John Doe",
            extra_field="extra_value"  # This should be ignored
        )
        assert applicant.applicant_name == "John Doe"
        # extra_field won't be in the model instance

    def test_model_dump_method(self):
        """Test model dump functionality"""
        summary = IncomeCertificateSummary(
            applicant_name="John Doe",
            income_details={"total_gross_income": "50000"},
            source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
            citations={},
            bounding_boxes={}
        )

        dumped = summary.model_dump()
        assert "applicant_name" in dumped
        assert "source_documents" in dumped
        assert dumped["applicant_name"] == "John Doe"

    def test_bounding_boxes_field_in_all_summaries(self):
        """Test that all summary models have bounding_boxes field"""
        models_to_test = [
            IntegratedCertificateSummary,
            IncomeCertificateSummary,
            OBCCertificateSummary,
            EWSCertificateSummary,
            FamilyMemberCertificateSummary
        ]

        for model_class in models_to_test:
            # Create the appropriate instance based on model type
            if model_class == IncomeCertificateSummary:
                instance = model_class(
                    applicant_name="Test User",
                    income_details={"total_gross_income": "50000"},
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )
            elif model_class == EWSCertificateSummary:
                instance = model_class(
                    applicant_name="Test User",
                    asset_details={"gross_annual_income": "50000"},
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )
            elif model_class == FamilyMemberCertificateSummary:
                instance = model_class(
                    applicant_name="Test User",
                    deceased_details={"deceased_hof_name": "HOF", "father_husband_name": "FH", "date_of_death": "2023-01-01"},
                    family_members_of_hof=[{"name": "Family Member", "gender": "Male", "relationship_with_hof": "Son"}],
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )
            else:
                # For IntegratedCertificateSummary, OBCCertificateSummary
                instance = model_class(
                    applicant_name="Test User",
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )

            assert hasattr(instance, 'bounding_boxes')
            assert isinstance(instance.bounding_boxes, dict)

    def test_citations_field_in_all_summaries(self):
        """Test that all summary models have citations field"""
        models_to_test = [
            IntegratedCertificateSummary,
            IncomeCertificateSummary,
            OBCCertificateSummary,
            EWSCertificateSummary,
            FamilyMemberCertificateSummary
        ]

        for model_class in models_to_test:
            # Create the appropriate instance based on model type
            if model_class == IncomeCertificateSummary:
                instance = model_class(
                    applicant_name="Test User",
                    income_details={"total_gross_income": "50000"},
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )
            elif model_class == EWSCertificateSummary:
                instance = model_class(
                    applicant_name="Test User",
                    asset_details={"gross_annual_income": "50000"},
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )
            elif model_class == FamilyMemberCertificateSummary:
                instance = model_class(
                    applicant_name="Test User",
                    deceased_details={"deceased_hof_name": "HOF", "father_husband_name": "FH", "date_of_death": "2023-01-01"},
                    family_members_of_hof=[{"name": "Family Member", "gender": "Male", "relationship_with_hof": "Son"}],
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )
            else:
                # For IntegratedCertificateSummary, OBCCertificateSummary
                instance = model_class(
                    applicant_name="Test User",
                    source_documents=[{"document_title": "Test", "filename": "test.pdf"}],
                    citations={},
                    bounding_boxes={}
                )

            assert hasattr(instance, 'citations')
            assert isinstance(instance.citations, dict)