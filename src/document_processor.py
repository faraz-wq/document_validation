"""
Document Processor - Stage 1
Processes individual documents and extracts structured data using Gemini
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, asdict

from gemini_client import GeminiClient
from file_handler import FileHandler, FileMetadata
from config import Config

logger = logging.getLogger(__name__)

# Stage 1 Prompt - Exact specification from requirements
STAGE1_PROMPT = """You are tasked with digitizing and extracting all data from an uploaded form/document. Follow these strict formatting rules for the output:

1. **Format:** Output the data using simple "key: value" text, with one key-value pair per line.

2. **Line Separation:** Place a mandatory, extra line break (blank line) after every single key-value entry to maximize separation and readability.

3. **Data Completeness:** Extract and include every single field, even if the value is blank, in which case use "(Not specified)".

4. **Field Naming:** Use clear and descriptive field names (keys).

5. **Handling Options/Checkmarks:** For any field that presents options (e.g., YES/NO, CENTRAL/STATE):
   * List all available options in the value section.
   * Explicitly state the "Selection" after the options.
   * If a selection can be determined from the source (e.g., a checkmark, slash, or circle), identify and state that selection.
   * If no clear selection is made, state "Selection: (Not specified)".

**Example Output Structure:**

Full name of the Applicant: [Extracted Name]

Gender: [Extracted Gender]

Whether Tax Paid: YES/NO [Selection: NO]

Services: CENTRAL/STATE [Options: CENTRAL/STATE] [Selection: (Not specified)]"""

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
        logger.info("DocumentProcessor initialized")

    def process_document(
        self,
        file_path: Path,
        document_name: Optional[str] = None
    ) -> DocumentExtractionResult:
        """
        Process a single document (PDF or image) using Gemini

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

            # Log warnings for multi-page PDFs
            if metadata.is_multi_page:
                logger.info(f"📄 Multi-page document detected: {metadata.page_count} pages")
                logger.info("   All pages will be sent to Gemini for processing")

            if metadata.potential_multi_doc:
                logger.warning("⚠️  WARNING: This PDF may contain MULTIPLE DOCUMENTS")
                logger.warning(f"   File has {metadata.page_count} pages - consider:")
                logger.warning("   1. Reviewing extracted results carefully")
                logger.warning("   2. Splitting PDF into separate documents if needed")
                logger.warning("   3. Verifying no documents/pages were skipped")

            # Use custom name if provided, otherwise use filename
            doc_name = document_name or file_path.stem

            # Send to Gemini for processing
            logger.info(f"Sending {file_path.name} to Gemini for Stage 1 processing...")
            extracted_text = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=STAGE1_PROMPT,
                wait_for_processing=True
            )

            # Analyze extraction for completeness
            self._analyze_extraction_completeness(file_path, metadata, extracted_text)

            # Create result object
            result = DocumentExtractionResult(
                document_id=metadata.document_id,
                file_name=file_path.name,
                file_metadata=metadata.to_dict(),
                extracted_text=extracted_text,
                processing_timestamp=datetime.now().isoformat(),
                success=True
            )

            logger.info(f"✓ Document processed successfully: {file_path.name}")
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

    def _analyze_extraction_completeness(
        self,
        file_path: Path,
        metadata: Any,
        extracted_text: str
    ) -> None:
        """
        Analyze extraction results for potential issues

        Args:
            file_path: Original file path
            metadata: File metadata object
            extracted_text: Extracted text from Gemini
        """
        # Count extracted fields
        field_count = extracted_text.count(':')
        logger.info(f"  → Extracted approximately {field_count} fields")

        # For multi-page PDFs, provide guidance
        if metadata.is_multi_page and metadata.page_count:
            # Rough estimate: expect at least 5-10 fields per page
            min_expected_fields = metadata.page_count * 5
            max_expected_fields = metadata.page_count * 15

            if field_count < min_expected_fields:
                logger.warning(
                    f"  ⚠ Extracted only {field_count} fields from {metadata.page_count}-page PDF"
                )
                logger.warning(f"     Expected at least {min_expected_fields} fields")
                logger.warning("     Some pages may have been skipped or poorly extracted")
            elif field_count > max_expected_fields:
                logger.info(
                    f"  → High field count ({field_count}) for {metadata.page_count}-page PDF"
                )
                logger.info("     This may indicate multiple documents in single PDF")

        # Check for document boundary indicators
        boundary_indicators = [
            "--- page",
            "page 1",
            "page 2",
            "page 3",
            "document 1",
            "document 2",
            "next page",
            "continued on",
            "см. на следующей странице"  # Multi-language support
        ]

        found_indicators = [
            ind for ind in boundary_indicators
            if ind.lower() in extracted_text.lower()
        ]

        if found_indicators:
            logger.info(f"  → Detected page/document boundaries: {', '.join(found_indicators)}")
            if metadata.is_multi_page:
                logger.info("     This suggests Gemini is processing multiple pages correctly")

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
