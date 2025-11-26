"""
Form Templates Module
Provides template-based field extraction for common document types
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class TemplateField:
    """Definition of a field in a form template"""
    field_name: str
    patterns: List[str]  # Regex patterns to match the field
    required: bool = False
    field_type: str = "text"  # text, date, number, checkbox, etc.

@dataclass
class FormTemplate:
    """Definition of a form template with its fields"""
    name: str
    description: str
    field_patterns: List[TemplateField]
    confidence_threshold: float = 0.7  # Minimum confidence to use this template
    
    def match_confidence(self, text: str) -> float:
        """
        Calculate how well this template matches the given text
        
        Args:
            text: Text content to compare against template
            
        Returns:
            Confidence score between 0 and 1
        """
        text_lower = text.lower()
        matched_patterns = 0
        total_patterns = 0
        
        # Count how many identifying keywords appear in the text
        keywords = ['income', 'certificate', 'application', 'form', 'aadhar', 'ration', 'family']  # Common doc keywords
        
        for field in self.field_patterns:
            total_patterns += 1
            for pattern in field.patterns:
                # Create a simple search pattern from the field pattern
                search_term = pattern.lower().replace(r'\s*[:\-]?\s*', ' ').replace(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', ' ')
                if re.search(search_term.strip(), text_lower, re.IGNORECASE):
                    matched_patterns += 1
                    break
        
        if total_patterns == 0:
            return 0.0
        
        return matched_patterns / total_patterns

class FormTemplateMatcher:
    """Matches documents to appropriate templates and extracts fields"""
    
    def __init__(self):
        self.templates = self._create_templates()
    
    def _create_templates(self) -> Dict[str, FormTemplate]:
        """Create and return dictionary of form templates"""
        templates = {}
        
        # Income Certificate Template
        income_template = FormTemplate(
            name="Income Certificate",
            description="Income certificate application form",
            field_patterns=[
                TemplateField("Applicant Full Name", [r'(?:Full Name|Name|Applicant Name)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 
                                                    r'(?:Applicant Full Name|Full Name of Applicant)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']),
                TemplateField("Father's Name", [r'(?:Father\'?s Name|Father Name|Father)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                                               r'(?:Father\'?s Full Name)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']),
                TemplateField("Date of Birth", [r'(?:Date of Birth|DOB|Birth Date)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})',
                                               r'(?:DOB)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})']),
                TemplateField("Age", [r'(?:Age)\s*[:\-]?\s*(\d{1,3})']),
                TemplateField("Gender", [r'(?:Gender|Sex)\s*[:\-]?\s*(Male|Female|Other|M|F|O)', 
                                        r'(?:M|F)\s*[:\-]?\s*(Male|Female|Male|Female)']),
                TemplateField("Address", [r'(?:Address|Permanent Address|Current Address)\s*[:\-]?\s*([A-Za-z0-9\s,.\-#]+?)(?:\n|$)',
                                        r'(?:Residential Address)\s*[:\-]?\s*([A-Za-z0-9\s,.\-#]+?)(?:\n|$)']),
                TemplateField("Annual Income", [r'(?:Annual Income|Total Income|Income)\s*[:\-]?\s*([₹$€£\d,.\s]+)',
                                               r'(?:Gross Annual Income)\s*[:\-]?\s*([₹$€£\d,.\s]+)']),
                TemplateField("Occupation", [r'(?:Occupation|Profession|Employment|Job)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("Religion", [r'(?:Religion)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("Caste", [r'(?:Caste|Category)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("Aadhar Number", [r'(?:Aadhar|Aadhaar)\s*[:\-]?\s*(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}|\d{12})']),
                TemplateField("Phone Number", [r'(?:Phone|Mobile|Contact)\s*[:\-]?\s*(\d{10}|\d{5}[\s\-]?\d{5})']),
                TemplateField("Email", [r'(?:Email|E-mail|Email ID)\s*[:\-]?\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})']),
                TemplateField("Signature", [r'(?:Signature|Sign|Applicant Sign)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("Date of Application", [r'(?:Date of Application|Application Date)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})']),
            ],
            confidence_threshold=0.4
        )
        
        # Aadhar Card Template
        aadhar_template = FormTemplate(
            name="Aadhar Card",
            description="Aadhar card document",
            field_patterns=[
                TemplateField("Aadhar Number", [r'(?:Aadhar|Aadhaar)\s*[:\-]?\s*(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}|\d{12})',
                                                r'(\d{4}[\s\-]?\d{4}[\s\-]?\d{4}|\d{12})']),  # Standalone numbers too
                TemplateField("Name", [r'(?:Name)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                                      r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})']),  # Names in the document
                TemplateField("Date of Birth", [r'(?:DOB|Date of Birth|YOB|Year of Birth)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})',
                                               r'(?:DOB)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})']),
                TemplateField("Gender", [r'(?:Gender|Sex)\s*[:\-]?\s*(Male|Female|Other|M|F|O)']),
                TemplateField("Address", [r'(?:Address)\s*:?\s*([A-Za-z0-9\s,.\-#]+?)(?:\n|Pincode|\s{2,})',
                                        r'(?:Address)\s+([A-Za-z0-9\s,.\-#]+?)(?=Document)']),
                TemplateField("Pincode", [r'(?:Pincode|Pin Code|Pin-Code)\s*[:\-]?\s*(\d{6})']),
                TemplateField("Enrollment Number", [r'(?:Enrollment No\.?|Enrollment Number)\s*[:\-]?\s*(\d{3}[-\s]?\d{7}[-\s]?\d{3})']),
            ],
            confidence_threshold=0.3
        )
        
        # Ration Card Template
        ration_template = FormTemplate(
            name="Ration Card",
            description="Ration card document",
            field_patterns=[
                TemplateField("Ration Card Number", [r'(?:Ration Card No\.?|Card No\.?|Card Number)\s*[:\-]?\s*([A-Z0-9]+)']),
                TemplateField("Family ID", [r'(?:Family ID|Family No\.?|Family Number)\s*[:\-]?\s*(\d+)']),
                TemplateField("Head of Family", [r'(?:Head of the Family|HOF|Head Name)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']),
                TemplateField("Address", [r'(?:Address|Permanent Address)\s*[:\-]?\s*([A-Za-z0-9\s,.\-#]+?)(?:\n|$)']),
                TemplateField("District", [r'(?:District|Dist\.?)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("State", [r'(?:State)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("Total Family Members", [r'(?:Total Family Members|Family Size|No\.? of Members)\s*[:\-]?\s*(\d+)']),
                TemplateField("Category", [r'(?:Category|Card Type)\s*[:\-]?\s*(Antyodaya Anna Yojana|APL|BPL|Priority Household|PHH)']),
                TemplateField("Member Name", [r'(?:Member Name|Name)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']),
                TemplateField("Age", [r'(?:Age)\s*[:\-]?\s*(\d{1,3})']),
                TemplateField("Gender", [r'(?:Gender|Sex)\s*[:\-]?\s*(Male|Female|Other|M|F|O)']),
                TemplateField("Relationship", [r'(?:Relationship|Relation)\s*[:\-]?\s*(Husband|Wife|Son|Daughter|Father|Mother|Brother|Sister|Self|Other)']),
            ],
            confidence_threshold=0.4
        )
        
        # Integrated Certificate Template
        integrated_template = FormTemplate(
            name="Integrated Certificate",
            description="Integrated Community, Nativity, DOB Certificate",
            field_patterns=[
                TemplateField("Full Name", [r'(?:Name|Full Name|Applicant Name)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']),
                TemplateField("Father's Name", [r'(?:Father\'?s Name|Father Name|Father)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']),
                TemplateField("Mother's Name", [r'(?:Mother\'?s Name|Mother Name|Mother)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']),
                TemplateField("Date of Birth", [r'(?:Date of Birth|DOB|Birth Date)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})']),
                TemplateField("Place of Birth", [r'(?:Place of Birth|Birth Place)\s*[:\-]?\s*([A-Za-z\s,.\-#]+)']),
                TemplateField("Gender", [r'(?:Gender|Sex)\s*[:\-]?\s*(Male|Female|Other|M|F|O)']),
                TemplateField("Caste", [r'(?:Caste|Community|Category)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("Religion", [r'(?:Religion)\s*[:\-]?\s*([A-Za-z\s]+)']),
                TemplateField("Nativity", [r'(?:Nativity|Native Place|Native of)\s*[:\-]?\s*([A-Za-z\s,.\-#]+)']),
                TemplateField("Annual Income", [r'(?:Annual Income|Total Income|Family Income)\s*[:\-]?\s*([₹$€£\d,.\s]+)']),
                TemplateField("Address", [r'(?:Address|Current Address|Permanent Address)\s*[:\-]?\s*([A-Za-z0-9\s,.\-#]+?)(?:\n|$)']),
                TemplateField("Phone", [r'(?:Phone|Mobile|Contact)\s*[:\-]?\s*(\d{10}|\d{5}[\s\-]?\d{5})']),
            ],
            confidence_threshold=0.4
        )
        
        templates["income"] = income_template
        templates["aadhar"] = aadhar_template
        templates["ration"] = ration_template
        templates["integrated"] = integrated_template
        
        return templates
    
    def find_best_template(self, text: str) -> Optional[Tuple[FormTemplate, float]]:
        """
        Find the best matching template for the given text
        
        Args:
            text: Text content to match against templates
            
        Returns:
            Tuple of (best template, confidence score) or None if no good match
        """
        best_template = None
        best_confidence = 0.0
        
        for template_name, template in self.templates.items():
            confidence = template.match_confidence(text)
            if confidence > best_confidence and confidence >= template.confidence_threshold:
                best_confidence = confidence
                best_template = template
        
        return (best_template, best_confidence) if best_template else None
    
    def extract_from_template(self, text: str, template: FormTemplate) -> Dict[str, str]:
        """
        Extract fields from text using a specific template
        
        Args:
            text: Text content to extract from
            template: Template to use for extraction
            
        Returns:
            Dictionary of field names and extracted values
        """
        results = {}
        
        for field in template.field_patterns:
            for pattern in field.patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Use the first match for now
                    match = matches[0]
                    if isinstance(match, tuple):
                        match = match[0]  # Get first captured group
                    results[field.field_name] = match.strip()
                    break  # Break after first successful match per field
            # If no match found and field is required, mark as missing
            if field.required and field.field_name not in results:
                results[field.field_name] = "(Not found - required)"
        
        return results
    
    def validate_extraction(self, extracted_data: Dict[str, str], template: FormTemplate) -> Dict[str, any]:
        """
        Validate that required fields were extracted

        Args:
            extracted_data: Dictionary of extracted fields
            template: Template used for extraction

        Returns:
            Dictionary with validation results including completeness score and detailed results
        """
        validation_results = {}
        total_required = 0
        found_required = 0

        for field in template.field_patterns:
            is_found = field.field_name in extracted_data and extracted_data[field.field_name] != "(Not found - required)" and extracted_data[field.field_name].strip() != ""
            validation_results[field.field_name] = {
                'found': is_found,
                'required': field.required,
                'value': extracted_data.get(field.field_name, '')
            }

            if field.required:
                total_required += 1
                if is_found:
                    found_required += 1

        completeness_score = found_required / total_required if total_required > 0 else 1.0

        return {
            'completeness_score': completeness_score,
            'total_required_fields': total_required,
            'found_required_fields': found_required,
            'missing_required_fields': [field for field, result in validation_results.items()
                                       if result['required'] and not result['found']],
            'field_validation_results': validation_results
        }

    def get_field_validation_report(self, extracted_text: str) -> Dict[str, any]:
        """
        Generate a comprehensive validation report for extracted text

        Args:
            extracted_text: The full extracted text to validate

        Returns:
            Comprehensive validation report
        """
        # Parse the extracted text into fields
        extracted_fields = self._parse_extracted_text_to_dict(extracted_text)

        # Try to find best matching template
        template_match = self.find_best_template(extracted_text)

        if template_match:
            template, confidence = template_match
            validation = self.validate_extraction(extracted_fields, template)

            return {
                'template_match': {
                    'name': template.name,
                    'confidence': confidence,
                    'description': template.description
                },
                'validation_results': validation,
                'extraction_quality': self._assess_extraction_quality(extracted_text, validation)
            }
        else:
            # Without template, do basic validation
            extracted_fields = self._parse_extracted_text_to_dict(extracted_text)
            return {
                'template_match': None,
                'validation_results': {
                    'completeness_score': 0,
                    'total_required_fields': 0,
                    'found_required_fields': 0,
                    'missing_required_fields': [],
                    'field_validation_results': {field: {'found': True, 'required': False, 'value': value}
                                                 for field, value in extracted_fields.items()}
                },
                'extraction_quality': self._assess_extraction_quality(extracted_text, {})
            }

    def _parse_extracted_text_to_dict(self, extracted_text: str) -> Dict[str, str]:
        """
        Parse the extracted text into a dictionary of field-value pairs

        Args:
            extracted_text: Text with "Field Name: Value" format

        Returns:
            Dictionary of field names to values
        """
        fields = {}
        lines = extracted_text.split('\n')

        for line in lines:
            line = line.strip()
            if ':' in line and not line.startswith('==='):
                # Split on first colon to handle values that contain colons
                parts = line.split(':', 1)
                if len(parts) == 2:
                    field_name = parts[0].strip()
                    field_value = parts[1].strip()
                    if field_name and field_value:
                        fields[field_name] = field_value

        return fields

    def _assess_extraction_quality(self, extracted_text: str, validation_results: Dict) -> str:
        """
        Assess the overall quality of the extraction

        Args:
            extracted_text: The extracted text
            validation_results: Results from field validation

        Returns:
            Quality assessment as a string (e.g. "High", "Medium", "Low")
        """
        if validation_results and 'completeness_score' in validation_results:
            score = validation_results['completeness_score']
            if score >= 0.8:
                return "High"
            elif score >= 0.5:
                return "Medium"
            else:
                return "Low"

        # If no validation results, assess based on text length and structure
        lines = [line.strip() for line in extracted_text.split('\n') if ':' in line and not line.startswith('===')]
        total_lines_with_colon = len(lines)

        if total_lines_with_colon >= 5:
            return "Medium to High"
        elif total_lines_with_colon >= 2:
            return "Medium"
        else:
            return "Low"

    def perform_accuracy_validation(self, extracted_text: str) -> Dict[str, any]:
        """
        Perform detailed accuracy validation on extracted text

        Args:
            extracted_text: The full extracted text to validate

        Returns:
            Detailed accuracy validation report
        """
        # Parse the extracted text into fields
        extracted_fields = self._parse_extracted_text_to_dict(extracted_text)

        # Check for potential data quality issues
        validation_issues = []

        # Check for empty or placeholder values
        for field_name, value in extracted_fields.items():
            if value.strip() == "" or value.strip() == "(Not specified)" or value.strip() == "(Not found - required)":
                validation_issues.append({
                    'field': field_name,
                    'issue': 'empty_or_placeholder',
                    'description': f"Field '{field_name}' has empty or placeholder value: '{value}'"
                })
            elif len(value) == 1 and value in ['X', 'x', '✓', 'V', 'v']:  # Likely a checkmark misinterpreted as value
                validation_issues.append({
                    'field': field_name,
                    'issue': 'checkmark_misidentified',
                    'description': f"Field '{field_name}' might contain a checkmark instead of actual value: '{value}'"
                })
            elif value.replace(' ', '').isalpha() and len(value) == 1:
                # Single letter that might be a checkmark
                validation_issues.append({
                    'field': field_name,
                    'issue': 'potential_checkmark',
                    'description': f"Field '{field_name}' has single letter value that might be a checkmark: '{value}'"
                })

        # Check for common extraction patterns that indicate problems
        if "Not specified" in extracted_text:
            count = extracted_text.count("Not specified")
            if count > len(extracted_fields) * 0.5:  # More than 50% are "Not specified"
                validation_issues.append({
                    'field': 'overall_extraction',
                    'issue': 'high_placeholder_rate',
                    'description': f"High rate of 'Not specified' values ({count}/{len(extracted_fields)}), indicating potential extraction problems"
                })

        # Try to find best matching template
        template_match = self.find_best_template(extracted_text)

        accuracy_report = {
            'validation_issues': validation_issues,
            'total_fields': len(extracted_fields),
            'issue_count': len(validation_issues),
            'template_match': template_match[0].name if template_match else None,
            'template_confidence': template_match[1] if template_match else 0.0,
            'accuracy_score': self._calculate_accuracy_score(extracted_fields, validation_issues),
            'data_quality_assessment': self._assess_data_quality(extracted_fields, validation_issues)
        }

        return accuracy_report

    def _calculate_accuracy_score(self, extracted_fields: Dict[str, str], validation_issues: List[Dict]) -> float:
        """
        Calculate an accuracy score based on the number and severity of validation issues

        Args:
            extracted_fields: Dictionary of extracted fields
            validation_issues: List of validation issues found

        Returns:
            Accuracy score between 0 and 1
        """
        if not extracted_fields:
            return 0.0

        # Start with perfect score
        score = 1.0

        # Deduct points for different types of issues
        for issue in validation_issues:
            issue_type = issue['issue']
            if issue_type == 'empty_or_placeholder':
                score -= 0.1  # Small deduction for empty fields
            elif issue_type == 'checkmark_misidentified':
                score -= 0.2  # Medium deduction for misidentified checkmarks
            elif issue_type == 'potential_checkmark':
                score -= 0.15  # Medium deduction for potential checkmark issues
            elif issue_type == 'high_placeholder_rate':
                score -= 0.3  # Large deduction for high placeholder rate

        # Ensure score doesn't go below 0
        return max(0.0, min(1.0, score))

    def _assess_data_quality(self, extracted_fields: Dict[str, str], validation_issues: List[Dict]) -> str:
        """
        Assess overall data quality based on validation results

        Args:
            extracted_fields: Dictionary of extracted fields
            validation_issues: List of validation issues found

        Returns:
            Quality assessment as a string
        """
        if not extracted_fields:
            return "Very Poor"

        issue_ratio = len(validation_issues) / len(extracted_fields) if extracted_fields else 0

        if issue_ratio == 0:
            return "Excellent"
        elif issue_ratio < 0.1:
            return "Good"
        elif issue_ratio < 0.25:
            return "Fair"
        elif issue_ratio < 0.5:
            return "Poor"
        else:
            return "Very Poor"