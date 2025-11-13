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

            # Use custom name if provided, otherwise use filename
            doc_name = document_name or file_path.stem

            # Send to Gemini for processing
            extracted_text = self.gemini_client.generate_content_with_file(
                file_path=file_path,
                prompt=STAGE1_PROMPT,
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
