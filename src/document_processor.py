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

logger = logging.getLogger(__name__)

# Stage 1 Prompt - Enhanced specification for comprehensive field extraction
STAGE1_FULL_DOCUMENT_PROMPT = """You are tasked with digitizing and extracting ALL data from the uploaded form/document. Follow these strict formatting rules for the output:

1. **Format:** Output the data using simple "key: value" text, with one key-value pair per line.

2. **Line Separation:** Place a mandatory, extra line break (blank line) after every single key-value entry to maximize separation and readability.

3. **Data Completeness:** Extract and include every single field, even if the value is blank, in which case use "(Not specified)".
   - Extract ALL visible text, checkmarks, checkboxes, radio buttons, signatures, stamps, and any other elements
   - Include section headers, form titles, and any organizational elements
   - For tables, extract each cell as a separate field with descriptive names
   - For forms with multiple sections, clearly label each section

4. **Field Naming:** Use clear and descriptive field names (keys) that reflect the field's purpose and location.
   - Include positioning information like "Section_X_Field_Y" when appropriate
   - Use standardized prefixes like "Applicant_", "Father_", "Income_", etc.

5. **Handling Options/Checkmarks:** For any field that presents options (e.g., YES/NO, CENTRAL/STATE):
   * List all available options in the value section.
   * Explicitly state the "Selection" after the options.
   * If a selection can be determined from the source (e.g., a checkmark, slash, or circle), identify and state that selection.
   * If no clear selection is made, state "Selection: (Not specified)".

6. **Table and Form Detection:** For tables or structured data:
   * Extract each cell with a descriptive field name that includes row and column information
   * Example: "Table_1_Row_2_Col_1_Description: [Value]"

7. **Signature and Stamp Detection:** Note any signatures or official stamps.
   * Example: "Signature_Authority: [Signature details if visible]"
   * Example: "Official_Stamp: [Description of stamp if visible]"

**CRITICAL:** Do not stop at the first few fields. Continue scanning the entire document to ensure ALL fields are captured.

**Example Output Structure:**

Document Title: [Extracted Title]

Full name of the Applicant: [Extracted Name]

Father's Name: [Father's Name]

Gender: [Extracted Gender]

Date of Birth: [DOB if available]

Whether Tax Paid: YES/NO [Options: YES/NO] [Selection: NO]

Services: CENTRAL/STATE [Options: CENTRAL/STATE] [Selection: (Not specified)]

Section A Field 1: [Value]

Section A Field 2: [Value]

Table_1_Row_1_Col_1_Description: [Value]"""

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
                # For images and other formats, use standard processing
                logger.info(f"Processing non-PDF file: {file_path.suffix}")
                extracted_text = self.gemini_client.generate_content_with_file(
                    file_path=file_path,
                    prompt=STAGE1_FULL_DOCUMENT_PROMPT,  # Updated to use enhanced prompt
                    wait_for_processing=True
                )

            # Create result object
            result = DocumentExtractionResult(
                document_id=metadata.document_id,
                file_name=file_path.name,
                file_metadata=metadata.to_dict(),
                extracted_text=extracted_text,
                processing_timestamp=datetime.now().isoformat(),
                success=True
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
                error_message=str(e)
            )
            return result

    def _process_pdf_with_pages(self, pdf_path: Path) -> str:
        """
        Process PDF by splitting into pages and extracting from each page

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Combined extracted text from all pages
        """
        logger.info(f"Processing PDF page-by-page: {pdf_path.name}")

        # Extract text from each page
        page_texts = self.pdf_processor.extract_text_from_pdf(pdf_path)
        logger.info(f"Extracted text from {len(page_texts)} pages")

        # Process each page with Gemini if it has substantial content
        page_extractions = []

        for page_num, page_text in enumerate(page_texts, 1):
            # Skip pages with very little content (likely blank pages)
            if len(page_text.strip()) < 50:
                logger.debug(f"Skipping page {page_num} - too little content ({len(page_text)} chars)")
                continue

            logger.info(f"Processing page {page_num}/{len(page_texts)}")

            # Create a temporary single-page PDF for this specific page
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_pdf_path = Path(temp_dir) / f"page_{page_num}.pdf"

                # Split PDF and get the specific page
                page_files = self.pdf_processor.split_pdf_to_pages(pdf_path, Path(temp_dir))

                if len(page_files) >= page_num:
                    # Process this specific page with Gemini
                    try:
                        page_extraction = self.gemini_client.generate_content_with_file(
                            file_path=page_files[page_num-1],  # 0-based index
                            prompt=get_page_specific_prompt(page_num),  # Updated to use new function
                            wait_for_processing=True
                        )

                        # Add a separator and page identifier
                        page_extraction_with_header = f"\n--- PAGE {page_num} EXTRACTION ---\n{page_extraction}\n--- END PAGE {page_num} ---\n"
                        page_extractions.append(page_extraction_with_header)
                    except Exception as e:
                        logger.warning(f"Error processing page {page_num}: {str(e)}")
                        # Fallback: use extracted text with basic field extraction
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
            combined_extraction = self.gemini_client.generate_content_with_file(
                file_path=pdf_path,
                prompt=STAGE1_FULL_DOCUMENT_PROMPT,
                wait_for_processing=True
            )

        logger.info(f"PDF processing complete, total extraction length: {len(combined_extraction)} characters")
        return combined_extraction

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
