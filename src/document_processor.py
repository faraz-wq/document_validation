"""
Document Processor - Stage 1
Processes individual documents and extracts structured data using Gemini
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

from src.gemini_client import GeminiClient
from src.file_handler import FileHandler, FileMetadata
from src.config import Config
from src.pdf_processor import PDFProcessor
from src.form_templates import FormTemplateMatcher

logger = logging.getLogger(__name__)

# Enhanced Stage 1 Prompts - Multi-step field extraction approach

# Initial comprehensive extraction prompt
STAGE1_FULL_DOCUMENT_PROMPT = """You are a precise document digitization specialist. Your task is to extract ALL data from the uploaded document with maximum completeness. Follow these steps:

**STEP 1: Initial Scanning**
First, provide a brief overview of all content visible on the document (1-2 sentences).

**STEP 2: Systematic Field Extraction**
Extract ALL possible fields using this exact format for each field:
- "Field Name: [Value]" (one per line, with blank line separation)
- Include ALL visible elements: text, checkmarks, checkboxes, radio buttons, signatures, stamps, headers, tables, etc.
- For missing/difficult-to-read values, write "(Not specified)" or "Partially visible: [what can be read]"

**STEP 3: Validation Check**
Double-check that you have captured:
- All name fields (applicant, father, mother, spouse, etc.)
- All date fields (DOB, issue dates, etc.)
- All address-related fields
- All financial fields (income, assets, etc.)
- All categorical fields (caste, community, etc.)
- All identification numbers (Aadhar, ration card, etc.)
- All signatures and stamps
- All checkmarks and selections

**OUTPUT FORMAT:**
Field Name: [Value]

Field Name: [Value]

(Blank line between each entry)

**EXAMPLE:**
Document Title: Income Certificate Application

Applicant Full Name: [Name]

Father's Name: [Father's Name]

Date of Birth: [DOB]

Gender: [Gender]

Annual Income: [Amount]

Signature Authority: [Signature details]

Selection Checkmark Yes: [X if checked, or "Not selected"]

Table Data Row 1 Column 1: [Value]"""

# Detailed field-specific extraction prompts for iterative processing
NAME_EXTRACTION_PROMPT = """Extract ALL name-related fields from this document. Provide output in key-value format with blank lines between entries:

Examples of name fields to look for:
- Applicant's name, full name, surname
- Father's name, mother's name, spouse name, children names
- Guardian name, nominee name
- Authorizing official name, issuing authority
- Witness names, referee names

Output Format:
Field Name: [Value]

Field Name: [Value]

(Blank line between each entry)"""

DATE_EXTRACTION_PROMPT = """Extract ALL date-related fields from this document. Provide output in key-value format with blank lines between entries:

Examples of date fields to look for:
- Date of birth, issue date, expiry date
- Application date, renewal date, registration date
- Employment start date, marriage date
- Any other date fields with DD/MM/YYYY, MM/DD/YYYY, or YYYY-MM-DD formats

Output Format:
Field Name: [Date Value]

Field Name: [Date Value]

(Blank line between each entry)"""

FINANCIAL_EXTRACTION_PROMPT = """Extract ALL financial and income-related fields from this document. Provide output in key-value format with blank lines between entries:

Examples of financial fields to look for:
- Salary, wages, income amounts
- Tax paid, deductions, net income
- Assets value, property value, vehicle value
- Bank account numbers, financial account details
- Amounts in any currency format

Output Format:
Field Name: [Amount/Value]

Field Name: [Amount/Value]

(Blank line between each entry)"""

IDENTIFICATION_EXTRACTION_PROMPT = """Extract ALL identification and number fields from this document. Provide output in key-value format with blank lines between entries:

Examples of identification fields to look for:
- Aadhar number, PAN number, voter ID
- Ration card number, driving license
- Passport number, employee ID, student ID
- Account numbers, registration numbers
- Certificate numbers, serial numbers

Output Format:
Field Name: [Number/ID]

Field Name: [Number/ID]

(Blank line between each entry)"""

CHECKMARK_EXTRACTION_PROMPT = """Extract ALL checkmarks, checkboxes, radio buttons, and selection indicators from this document. Provide output in key-value format with blank lines between entries:

For each checkmark/selection, provide:
- The associated field/option name
- Whether it's selected or not
- The context of what is being selected

Output Format:
Field Name Selection: [Selected/Not selected/difficult to determine]
Option Available: [List of options]
Selection Detail: [What's specifically selected]

(Blank line between each entry)"""

TABLE_EXTRACTION_PROMPT = """Extract ALL table data from this document. For each table, provide data in a structured key-value format with blank lines between entries:

For each table cell, create a field name that includes row/column position:
- Example: "Table_1_Row_2_Col_3_Description: [Value]"
- Include header row values as context
- If table spans multiple pages, note the continuation

Output Format:
Table_Field_Name: [Value]

Table_Field_Name: [Value]

(Blank line between each entry)"""

def get_page_specific_prompt(page_num: int) -> str:
    """
    Get a prompt specifically for a given page number to ensure comprehensive extraction

    Args:
        page_num: The page number being processed

    Returns:
        A specialized prompt for the given page
    """
    return f"""You are tasked with digitizing and extracting ALL data from page {page_num} of an uploaded document. Follow these strict formatting rules for the output:

1. **Format:** Output the data using simple "key: value" text, with one key-value pair per line.

2. **Line Separation:** Place a mandatory, extra line break (blank line) after every single key-value entry to maximize separation and readability.

3. **Data Completeness:** Extract and include every single field visible on this page, even if the value is blank, in which case use "(Not specified)".
   - Extract ALL visible text, checkmarks, checkboxes, radio buttons, signatures, stamps, and any other elements
   - Include section headers, form titles, and any organizational elements on this page
   - For tables on this page, extract each cell as a separate field with descriptive names
   - Pay special attention to continuation fields from previous pages

4. **Field Naming:** Use clear and descriptive field names (keys) that reflect the field's purpose and location.
   - Include positioning information like "Page_{page_num}_Section_X_Field_Y" when appropriate
   - Use standardized prefixes like "Applicant_", "Father_", "Income_", etc.

5. **Handling Options/Checkmarks:** For any field that presents options (e.g., YES/NO, CENTRAL/STATE):
   * List all available options in the value section.
   * Explicitly state the "Selection" after the options.
   * If a selection can be determined from the source (e.g., a checkmark, slash, or circle), identify and state that selection.
   * If no clear selection is made, state "Selection: (Not specified)".

6. **Table and Form Detection:** For tables or structured data on this page:
   * Extract each cell with a descriptive field name that includes row and column information
   * Example: "Page_{page_num}_Table_1_Row_2_Col_1_Description: [Value]"

7. **Signature and Stamp Detection:** Note any signatures or official stamps on this page.
   * Example: "Page_{page_num}_Signature_Authority: [Signature details if visible]"
   * Example: "Page_{page_num}_Official_Stamp: [Description of stamp if visible]"

**IMPORTANT:** Focus on extracting ALL elements visible on page {page_num}. Do not miss any fields that might continue from previous pages or continue to future pages. Ensure comprehensive extraction from this specific page.

**Example Output Structure:**

Page {page_num} Document Title: [Extracted Title]

Page {page_num} Full name of the Applicant: [Extracted Name]

Page {page_num} Father's Name: [Father's Name]

Page {page_num} Gender: [Extracted Gender]

Page {page_num} Whether Tax Paid: YES/NO [Options: YES/NO] [Selection: NO]

Page {page_num} Services: CENTRAL/STATE [Options: CENTRAL/STATE] [Selection: (Not specified)]"""

@dataclass
class DocumentExtractionResult:
    """Result from Stage 1 document processing"""
    document_id: str
    file_name: str
    file_metadata: Dict
    extracted_text: str
    processing_timestamp: str
    success: bool
    error_message: Optional[str] = None
    page_count: Optional[int] = None  # Added to track number of pages processed
    page_extractions: Optional[List[str]] = None  # Added to store individual page extractions
    extraction_validation: Optional[Dict] = None  # Added to store validation results

    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert result to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

class DocumentProcessor:
    """Stage 1: Process individual documents to extract structured data"""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """
        Initialize document processor

        Args:
            gemini_client: Gemini client instance (creates new one if not provided)
        """
        self.gemini_client = gemini_client or GeminiClient()
        self.pdf_processor = PDFProcessor()
        self.template_matcher = FormTemplateMatcher()
        logger.info("DocumentProcessor initialized")

    def process_document(
        self,
        file_path: Path,
        document_name: Optional[str] = None
    ) -> DocumentExtractionResult:
        """
        Process a single document (PDF or image) using Gemini
        For PDFs, processes each page individually to capture all fields

        Args:
            file_path: Path to document file
            document_name: Optional custom name for the document

        Returns:
            DocumentExtractionResult object
        """
        from datetime import datetime

        logger.info(f"Processing document: {file_path.name}")

        try:
            # Get file metadata
            metadata = FileHandler.get_file_metadata(file_path)

            # Use custom name if provided, otherwise use filename
            doc_name = document_name or file_path.stem

            # Check if file is a PDF and handle page-by-page extraction if needed
            if file_path.suffix.lower() == '.pdf':
                logger.info(f"Processing PDF file with {metadata.page_count or 'unknown'} pages")
                extracted_text = self._process_pdf_with_pages(file_path)
            else:
                # For images and other formats, use multi-step extraction
                logger.info(f"Processing non-PDF file: {file_path.suffix}")
                extracted_text = self._process_single_document_full_extraction(file_path)

            # Create result object
            result = DocumentExtractionResult(
                document_id=metadata.document_id,
                file_name=file_path.name,
                file_metadata=metadata.to_dict(),
                extracted_text=extracted_text,
                processing_timestamp=datetime.now().isoformat(),
                success=True
            )

            # Enhance extraction with template matching
            extracted_text = self._enhance_extraction_with_templates(extracted_text, file_path)

            # Perform comprehensive validation
            validation_report = self._perform_extraction_validation(extracted_text)

            # Create result object
            result = DocumentExtractionResult(
                document_id=metadata.document_id,
                file_name=file_path.name,
                file_metadata=metadata.to_dict(),
                extracted_text=extracted_text,
                processing_timestamp=datetime.now().isoformat(),
                success=True,
                extraction_validation=validation_report
            )

            logger.info(f"Document processed successfully: {file_path.name}")
            return result

        except Exception as e:
            logger.error(f"Error processing document {file_path.name}: {str(e)}")

            # Create error result
            result = DocumentExtractionResult(
                document_id=file_path.stem,
                file_name=file_path.name,
                file_metadata={},
                extracted_text="",
                processing_timestamp=datetime.now().isoformat(),
                success=False,
                error_message=str(e),
                extraction_validation=None
            )
            return result

    def _enhance_extraction_with_templates(self, extracted_text: str, file_path: Path) -> str:
        """
        Enhance the extracted text by applying form templates to ensure all fields are captured

        Args:
            extracted_text: Initial extraction from Gemini
            file_path: Path to the original file for context

        Returns:
            Enhanced extraction with template-based additions
        """
        logger.info(f"Enhancing extraction with template matching for: {file_path.name}")

        # Try to find the best matching template
        template_result = self.template_matcher.find_best_template(extracted_text)

        if template_result:
            template, confidence = template_result
            logger.info(f"Best matching template: {template.name} (confidence: {confidence:.2f})")

            # Extract fields using the template
            template_fields = self.template_matcher.extract_from_template(extracted_text, template)

            # Add template-extracted fields to the main extraction
            enhanced_extraction = extracted_text
            template_additions = []

            for field_name, value in template_fields.items():
                # Check if this field is already in the main extraction to avoid duplication
                field_already_present = False
                for existing_field in extracted_text.split('\n\n'):
                    if existing_field.startswith(f"{field_name}:"):
                        field_already_present = True
                        break

                if not field_already_present:
                    template_additions.append(f"{field_name}: {value}")

            if template_additions:
                # Add a section for template-matched fields
                enhanced_extraction += f"\n\n=== TEMPLATE-MATCHED FIELDS (Confidence: {confidence:.2f}) ===\n"
                enhanced_extraction += "\n\n".join(template_additions) + "\n"

            # Add validation of required fields
            validation_results = self.template_matcher.validate_extraction(template_fields, template)
            missing_fields = [field for field, found in validation_results.items() if not found and self._is_required_field(field, template)]

            if missing_fields:
                enhancement_note = f"\n\n=== VALIDATION NOTE ===\n"
                enhancement_note += f"Template used: {template.name}\n"
                enhancement_note += f"Confidence score: {confidence:.2f}\n"
                enhancement_note += f"Missing required fields: {', '.join(missing_fields)}\n"
                enhancement_note += "Consider re-processing or manual verification for these fields.\n"
                enhanced_extraction += enhancement_note

            return enhanced_extraction
        else:
            logger.info("No suitable template found for this document")
            return extracted_text

    def _perform_extraction_validation(self, extracted_text: str) -> Dict:
        """
        Perform comprehensive validation on the extracted text

        Args:
            extracted_text: The text to validate

        Returns:
            Validation report dictionary
        """
        logger.info("Performing comprehensive extraction validation")

        # Get validation report using the template matcher
        validation_report = self.template_matcher.get_field_validation_report(extracted_text)

        # Get detailed accuracy validation
        accuracy_report = self.template_matcher.perform_accuracy_validation(extracted_text)

        # Combine both reports
        full_report = {
            'template_validation': validation_report,
            'accuracy_validation': accuracy_report,
            'overall_assessment': self._calculate_overall_assessment(validation_report, accuracy_report)
        }

        return full_report

    def _calculate_overall_assessment(self, validation_report: Dict, accuracy_report: Dict) -> Dict[str, any]:
        """
        Calculate overall assessment based on both validation reports

        Args:
            validation_report: Template-based validation report
            accuracy_report: Accuracy-based validation report

        Returns:
            Overall assessment dictionary
        """
        # Get completeness score from template validation
        completeness_score = validation_report.get('validation_results', {}).get('completeness_score', 0)

        # Get accuracy score from accuracy validation
        accuracy_score = accuracy_report.get('accuracy_score', 0)

        # Calculate overall score as weighted average
        overall_score = (completeness_score * 0.4 + accuracy_score * 0.6)  # Slightly weight accuracy higher

        # Determine confidence level
        if overall_score >= 0.8:
            confidence_level = "High"
            message = "Extraction appears accurate and complete"
        elif overall_score >= 0.6:
            confidence_level = "Medium"
            message = "Extraction is reasonably accurate but may need review"
        elif overall_score >= 0.4:
            confidence_level = "Low"
            message = "Extraction may contain errors, manual verification recommended"
        else:
            confidence_level = "Very Low"
            message = "Extraction has significant issues, manual verification required"

        # Check for critical issues
        critical_issues = []
        if accuracy_report.get('issue_count', 0) > 0:
            for issue in accuracy_report.get('validation_issues', []):
                if issue['issue'] in ['high_placeholder_rate']:
                    critical_issues.append(issue['description'])

        return {
            'overall_score': overall_score,
            'completeness_score': completeness_score,
            'accuracy_score': accuracy_score,
            'confidence_level': confidence_level,
            'recommendation': message,
            'critical_issues': critical_issues,
            'requires_manual_review': overall_score < 0.6 or bool(critical_issues)
        }

    def _is_required_field(self, field_name: str, template: 'FormTemplate') -> bool:
        """Check if a field is marked as required in the template"""
        for template_field in template.field_patterns:
            if template_field.field_name == field_name:
                return template_field.required
        return False

    def _process_pdf_with_pages(self, pdf_path: Path) -> str:
        """
        Process PDF by splitting into pages and extracting from each page
        Uses multi-step field extraction for comprehensive coverage

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Combined extracted text from all pages
        """
        logger.info(f"Processing PDF page-by-page with multi-step extraction: {pdf_path.name}")

        # Extract text from each page
        page_texts = self.pdf_processor.extract_text_from_pdf(pdf_path)
        logger.info(f"Extracted text from {len(page_texts)} pages")

        # Process each page with Gemini using multiple extraction passes
        page_extractions = []

        for page_num, page_text in enumerate(page_texts, 1):
            # Skip pages with very little content (likely blank pages)
            if len(page_text.strip()) < 50:
                logger.debug(f"Skipping page {page_num} - too little content ({len(page_text)} chars)")
                continue

            logger.info(f"Processing page {page_num}/{len(page_texts)} with multi-step extraction")

            # Create a temporary single-page PDF for this specific page
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_pdf_path = Path(temp_dir) / f"page_{page_num}.pdf"

                # Split PDF and get the specific page
                page_files = self.pdf_processor.split_pdf_to_pages(pdf_path, Path(temp_dir))

                if len(page_files) >= page_num:
                    # Process this specific page with multiple extraction passes
                    try:
                        # First pass: General comprehensive extraction
                        general_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],  # 0-based index
                            prompt=get_page_specific_prompt(page_num),
                            wait_for_processing=True
                        )

                        # Second pass: Name-specific extraction
                        name_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],
                            prompt=NAME_EXTRACTION_PROMPT,
                            wait_for_processing=True
                        )

                        # Third pass: Date-specific extraction
                        date_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],
                            prompt=DATE_EXTRACTION_PROMPT,
                            wait_for_processing=True
                        )

                        # Fourth pass: Financial-specific extraction
                        financial_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],
                            prompt=FINANCIAL_EXTRACTION_PROMPT,
                            wait_for_processing=True
                        )

                        # Fifth pass: Identification-specific extraction
                        id_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],
                            prompt=IDENTIFICATION_EXTRACTION_PROMPT,
                            wait_for_processing=True
                        )

                        # Sixth pass: Checkmark-specific extraction
                        checkmark_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],
                            prompt=CHECKMARK_EXTRACTION_PROMPT,
                            wait_for_processing=True
                        )

                        # Seventh pass: Table-specific extraction
                        table_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],
                            prompt=TABLE_EXTRACTION_PROMPT,
                            wait_for_processing=True
                        )

                        # Combine all extractions for this page with clear section headers
                        page_extraction_raw = (f"\n=== GENERAL EXTRACTION ===\n{general_extraction}\n"
                                              f"\n=== NAME FIELDS ===\n{name_extraction}\n"
                                              f"\n=== DATE FIELDS ===\n{date_extraction}\n"
                                              f"\n=== FINANCIAL FIELDS ===\n{financial_extraction}\n"
                                              f"\n=== IDENTIFICATION FIELDS ===\n{id_extraction}\n"
                                              f"\n=== CHECKMARK FIELDS ===\n{checkmark_extraction}\n"
                                              f"\n=== TABLE DATA ===\n{table_extraction}\n")

                        # Apply accuracy verification to this page's extraction
                        verified_page_extraction = self._verify_extraction_accuracy(page_extraction_raw)

                        # Add page headers to verified extraction
                        page_extraction_with_header = f"\n--- PAGE {page_num} COMPREHENSIVE EXTRACTION ---\n{verified_page_extraction}\n--- END PAGE {page_num} ---\n"
                        page_extractions.append(page_extraction_with_header)

                        logger.info(f"Completed multi-step extraction for page {page_num}")

                    except Exception as e:
                        logger.warning(f"Error in multi-step processing for page {page_num}: {str(e)}")
                        # Fallback: use single extraction prompt
                        try:
                            page_extraction = self.gemini_client.generate_content_with_file(
                                file_path=page_files[page_num-1],
                                prompt=get_page_specific_prompt(page_num),
                                wait_for_processing=True
                            )
                            # Apply verification to fallback extraction too
                            verified_fallback_extraction = self._verify_extraction_accuracy(f"=== GENERAL EXTRACTION ===\n{page_extraction}")
                            page_extraction_with_header = f"\n--- PAGE {page_num} EXTRACTION (FALLBACK) ---\n{verified_fallback_extraction}\n--- END PAGE {page_num} ---\n"
                            page_extractions.append(page_extraction_with_header)
                        except Exception as fallback_error:
                            logger.warning(f"Fallback also failed for page {page_num}: {str(fallback_error)}")
                            # Final fallback: use extracted text with basic field extraction
                            basic_extraction = self._extract_basic_fields_from_text(page_text, page_num)
                            page_extraction_with_header = f"\n--- PAGE {page_num} EXTRACTION (BASIC) ---\n{basic_extraction}\n--- END PAGE {page_num} ---\n"
                            page_extractions.append(page_extraction_with_header)
                else:
                    logger.warning(f"Page {page_num} not found in split files")

        # Combine all page extractions
        combined_extraction = "\n".join(page_extractions)

        if not combined_extraction.strip():
            logger.warning("No content extracted from any page, falling back to full document processing")
            # If no content was extracted from individual pages, fall back to processing entire document
            combined_extraction = self._process_single_document_full_extraction(pdf_path)

        logger.info(f"PDF processing complete, total extraction length: {len(combined_extraction)} characters")
        return combined_extraction

    def _process_single_document_full_extraction(self, file_path: Path) -> str:
        """
        Process a single document (PDF or image) with comprehensive multi-step extraction

        Args:
            file_path: Path to document file

        Returns:
            Comprehensive extraction result
        """
        logger.info(f"Performing full multi-step extraction on: {file_path.name}")

        try:
            # Step 1: General comprehensive extraction
            general_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=STAGE1_FULL_DOCUMENT_PROMPT,
                wait_for_processing=True
            )

            # Step 2: Name-specific extraction
            name_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=NAME_EXTRACTION_PROMPT,
                wait_for_processing=True
            )

            # Step 3: Date-specific extraction
            date_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=DATE_EXTRACTION_PROMPT,
                wait_for_processing=True
            )

            # Step 4: Financial-specific extraction
            financial_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=FINANCIAL_EXTRACTION_PROMPT,
                wait_for_processing=True
            )

            # Step 5: Identification-specific extraction
            id_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=IDENTIFICATION_EXTRACTION_PROMPT,
                wait_for_processing=True
            )

            # Step 6: Checkmark-specific extraction
            checkmark_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=CHECKMARK_EXTRACTION_PROMPT,
                wait_for_processing=True
            )

            # Step 7: Table-specific extraction
            table_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=TABLE_EXTRACTION_PROMPT,
                wait_for_processing=True
            )

            # Combine all extractions with clear section headers
            full_extraction = (f"=== GENERAL EXTRACTION ===\n{general_extraction}\n"
                              f"\n=== NAME FIELDS ===\n{name_extraction}\n"
                              f"\n=== DATE FIELDS ===\n{date_extraction}\n"
                              f"\n=== FINANCIAL FIELDS ===\n{financial_extraction}\n"
                              f"\n=== IDENTIFICATION FIELDS ===\n{id_extraction}\n"
                              f"\n=== CHECKMARK FIELDS ===\n{checkmark_extraction}\n"
                              f"\n=== TABLE DATA ===\n{table_extraction}\n")

            # Apply accuracy validation and cross-verification
            verified_extraction = self._verify_extraction_accuracy(full_extraction)

            # Enhance with template matching
            verified_extraction = self._enhance_extraction_with_templates(verified_extraction, file_path)

            logger.info(f"Completed multi-step extraction for: {file_path.name}")
            return verified_extraction

        except Exception as e:
            logger.error(f"Multi-step extraction failed for {file_path.name}: {str(e)}")
            # Fall back to basic extraction
            logger.info("Falling back to basic extraction method")
            basic_extraction = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=STAGE1_FULL_DOCUMENT_PROMPT,
                wait_for_processing=True
            )
            # Apply verification to fallback extraction too
            basic_extraction = self._verify_extraction_accuracy(basic_extraction)
            # Also enhance the fallback extraction
            return self._enhance_extraction_with_templates(basic_extraction, file_path)

    def _verify_extraction_accuracy(self, extraction_text: str) -> str:
        """
        Verify extraction accuracy by cross-checking between different extraction passes
        and adding confidence scores to extracted fields

        Args:
            extraction_text: Raw extraction text from all passes

        Returns:
            Verified extraction with confidence indicators
        """
        logger.info("Verifying extraction accuracy with cross-validation")

        # Parse extractions by section
        sections = {}
        current_section = "unknown"
        current_content = []

        for line in extraction_text.split('\n'):
            if line.startswith('=== ') and line.endswith(' ==='):
                # Save previous section
                if current_section != "unknown":
                    sections[current_section] = '\n'.join(current_content)

                # Start new section
                current_section = line.strip(' ===')
                current_content = []
            else:
                current_content.append(line)

        # Save the last section
        if current_section != "unknown":
            sections[current_section] = '\n'.join(current_content)

        # Cross-verify fields between sections
        verified_content = extraction_text

        # Add accuracy verification section
        accuracy_report = self._generate_accuracy_report(sections)

        if accuracy_report:
            verified_content += f"\n\n=== ACCURACY VERIFICATION ===\n{accuracy_report}"

        return verified_content

    def _generate_accuracy_report(self, sections: Dict[str, str]) -> str:
        """
        Generate an accuracy report by cross-checking different extraction sections

        Args:
            sections: Dictionary of extraction sections

        Returns:
            Accuracy report as a string
        """
        report_parts = []

        # Check for consistency between general and specific extractions
        general_content = sections.get('GENERAL EXTRACTION', '')
        name_content = sections.get('NAME FIELDS', '')
        date_content = sections.get('DATE FIELDS', '')

        # Find duplicate or conflicting fields
        general_fields = self._parse_fields(general_content)
        name_fields = self._parse_fields(name_content)
        date_fields = self._parse_fields(date_content)

        # Compare names between sections
        name_conflicts = []
        for field_name, field_value in general_fields.items():
            if field_name in name_fields and name_fields[field_name] != field_value:
                name_conflicts.append(f"Conflict in '{field_name}': General='{field_value}' vs Name-specific='{name_fields[field_name]}'")

        if name_conflicts:
            report_parts.append(f"Name Conflicts Found: {len(name_conflicts)}")
            for conflict in name_conflicts:
                report_parts.append(f"  - {conflict}")
        else:
            report_parts.append("✓ No name conflicts detected between extraction methods")

        # Check date consistency
        date_conflicts = []
        for field_name, field_value in general_fields.items():
            if field_name in date_fields and date_fields[field_name] != field_value:
                date_conflicts.append(f"Conflict in '{field_name}': General='{field_value}' vs Date-specific='{date_fields[field_name]}'")

        if date_conflicts:
            report_parts.append(f"Date Conflicts Found: {len(date_conflicts)}")
            for conflict in date_conflicts:
                report_parts.append(f"  - {conflict}")
        else:
            report_parts.append("✓ No date conflicts detected between extraction methods")

        # Generate overall confidence score
        total_sections = len(sections)
        populated_sections = sum(1 for content in sections.values() if content.strip())
        confidence_score = populated_sections / total_sections if total_sections > 0 else 0

        report_parts.append(f"\nOverall Extraction Confidence: {confidence_score:.2%}")
        report_parts.append(f"Sections with content: {populated_sections}/{total_sections}")

        # Add recommendation based on confidence
        if confidence_score < 0.5:
            report_parts.append("⚠️  LOW CONFIDENCE: Manual verification recommended")
        elif confidence_score < 0.8:
            report_parts.append("⚠️  MEDIUM CONFIDENCE: Review recommended")
        else:
            report_parts.append("✅ HIGH CONFIDENCE: Extraction appears accurate")

        return "\n".join(report_parts)

    def _parse_fields(self, content: str) -> Dict[str, str]:
        """
        Parse field-value pairs from extraction content

        Args:
            content: Extraction content to parse

        Returns:
            Dictionary of field names to values
        """
        fields = {}
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            if ':' in line and not line.startswith('===') and not line.startswith('✓') and not line.startswith('⚠️'):
                # Split on first colon to handle values that contain colons
                parts = line.split(':', 1)
                if len(parts) == 2:
                    field_name = parts[0].strip()
                    field_value = parts[1].strip()
                    if field_name and field_value and field_value != "(Not specified)":
                        fields[field_name] = field_value

        return fields

    def _extract_basic_fields_from_text(self, text: str, page_num: int) -> str:
        """
        Extract basic fields from text as a fallback when Gemini fails

        Args:
            text: Text content to extract from
            page_num: Page number for reference

        Returns:
            Basic field extraction in the required format
        """
        # This is a basic extraction that identifies common fields
        import re

        extraction_lines = [f"PAGE {page_num} BASIC FIELD DETECTION\n"]

        # Look for common patterns
        patterns = [
            (r'(?:Name|NAME|name|Applicant Name|FullName|Full Name)[:\-\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'Name'),
            (r'(?:DOB|Date of Birth|Birth Date)[:\-\s]+(\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})', 'Date of Birth'),
            (r'(?:Father|Father\'?s Name)[:\-\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'Father\'s Name'),
            (r'(?:Address|ADDRESS|address)[:\-\s]+([A-Za-z0-9\s,.\-#]+?)(?:\n|$)', 'Address'),
            (r'(?:Phone|Phone Number|Mobile|Mobile Number)[:\-\s]+(\d{10}|\d{5}[-\s]?\d{5})', 'Phone Number'),
        ]

        for pattern, field_name in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    extraction_lines.append(f"{field_name}: {match.strip()}\n\n")

        # If no specific fields found, return the text content with labels
        if len(extraction_lines) <= 1:
            if text.strip():
                extraction_lines.append(f"Page {page_num} Content (Basic Extraction): {text[:500]}...\n\n")
            else:
                extraction_lines.append(f"Page {page_num} Content: (No content detected)\n\n")

        return "\n".join(extraction_lines)


    def process_batch(
        self,
        file_paths: list[Path],
        document_names: Optional[list[str]] = None
    ) -> list[DocumentExtractionResult]:
        """
        Process multiple documents in batch

        Args:
            file_paths: List of file paths
            document_names: Optional list of custom document names

        Returns:
            List of DocumentExtractionResult objects
        """
        logger.info(f"Processing batch of {len(file_paths)} documents")

        results = []
        for idx, file_path in enumerate(file_paths):
            doc_name = None
            if document_names and idx < len(document_names):
                doc_name = document_names[idx]

            result = self.process_document(file_path, doc_name)
            results.append(result)

        success_count = sum(1 for r in results if r.success)
        logger.info(
            f"Batch processing complete: {success_count}/{len(results)} successful"
        )

        return results

    def save_extraction_result(
        self,
        result: DocumentExtractionResult,
        output_dir: Optional[Path] = None
    ) -> Path:
        """
        Save extraction result to file

        Args:
            result: DocumentExtractionResult object
            output_dir: Output directory (uses Config.STAGE1_DIR if not provided)

        Returns:
            Path to saved file
        """
        output_dir = output_dir or Config.STAGE1_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save extracted text
        text_file = output_dir / f"{result.document_id}_extracted.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(result.extracted_text)

        # Save metadata as JSON
        json_file = output_dir / f"{result.document_id}_metadata.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(result.to_json())

        logger.info(f"Extraction result saved: {text_file.name}")
        return text_file

    def save_batch_results(
        self,
        results: list[DocumentExtractionResult],
        output_dir: Optional[Path] = None
    ) -> list[Path]:
        """
        Save batch extraction results

        Args:
            results: List of DocumentExtractionResult objects
            output_dir: Output directory

        Returns:
            List of paths to saved files
        """
        saved_paths = []
        for result in results:
            if result.success:
                path = self.save_extraction_result(result, output_dir)
                saved_paths.append(path)

        logger.info(f"Saved {len(saved_paths)} extraction results")
        return saved_paths
