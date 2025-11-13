"""
Summary Generator - Stage 2
Generates cross-document summary using consolidated data from Stage 1
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from gemini_client import GeminiClient
from certificate_types import CertificateType, CertificateSpecs
from document_processor import DocumentExtractionResult
from config import Config

logger = logging.getLogger(__name__)

# Stage 2 Prompt Template
STAGE2_PROMPT_TEMPLATE = """Extract the following summary fields from ALL provided document data. Generate the output as a three-column markdown table (Field, Value, Source Document(s)).

**Summary Fields List:**
{summary_fields}

{document_data}"""

@dataclass
class SummaryResult:
    """Result from Stage 2 summary generation"""
    certificate_type: str
    summary_table: str
    processing_timestamp: str
    document_count: int
    document_ids: List[str]
    success: bool
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert result to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert result to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

class SummaryGenerator:
    """Stage 2: Generate cross-document summary from extracted data"""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        """
        Initialize summary generator

        Args:
            gemini_client: Gemini client instance (creates new one if not provided)
        """
        self.gemini_client = gemini_client or GeminiClient()
        logger.info("SummaryGenerator initialized")

    def _build_document_section(
        self,
        extraction_results: List[DocumentExtractionResult]
    ) -> str:
        """
        Build document data section for Stage 2 prompt

        Args:
            extraction_results: List of Stage 1 extraction results

        Returns:
            Formatted document data string
        """
        sections = []

        for idx, result in enumerate(extraction_results, 1):
            if not result.success:
                logger.warning(f"Skipping failed document: {result.file_name}")
                continue

            section = f"**Document {idx}: {result.file_name}**\n{result.extracted_text}\n"
            sections.append(section)

        return "\n".join(sections)

    def _build_summary_fields_list(
        self,
        cert_type: CertificateType
    ) -> str:
        """
        Build formatted summary fields list for prompt

        Args:
            cert_type: Certificate type

        Returns:
            Formatted fields list
        """
        fields = CertificateSpecs.get_summary_fields(cert_type)
        formatted_fields = "\n".join(f"- {field}" for field in fields)
        return formatted_fields

    def generate_summary(
        self,
        extraction_results: List[DocumentExtractionResult],
        cert_type: CertificateType,
        document_names: Optional[List[str]] = None
    ) -> SummaryResult:
        """
        Generate cross-document summary from Stage 1 results

        Args:
            extraction_results: List of Stage 1 extraction results
            cert_type: Certificate type
            document_names: Optional custom document names

        Returns:
            SummaryResult object
        """
        logger.info(
            f"Generating summary for {cert_type.value} certificate "
            f"with {len(extraction_results)} documents"
        )

        try:
            # Build prompt components
            summary_fields = self._build_summary_fields_list(cert_type)
            document_data = self._build_document_section(extraction_results)

            # Build complete prompt
            prompt = STAGE2_PROMPT_TEMPLATE.format(
                summary_fields=summary_fields,
                document_data=document_data
            )

            # Send to Gemini for summary generation
            logger.info("Sending aggregated data to Gemini for summary generation")
            summary_table = self.gemini_client.generate_content_from_text(prompt)

            # Create result object
            result = SummaryResult(
                certificate_type=cert_type.value,
                summary_table=summary_table,
                processing_timestamp=datetime.now().isoformat(),
                document_count=len(extraction_results),
                document_ids=[r.document_id for r in extraction_results if r.success],
                success=True
            )

            logger.info("Summary generated successfully")
            return result

        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")

            # Create error result
            result = SummaryResult(
                certificate_type=cert_type.value,
                summary_table="",
                processing_timestamp=datetime.now().isoformat(),
                document_count=len(extraction_results),
                document_ids=[],
                success=False,
                error_message=str(e)
            )
            return result

    def save_summary_result(
        self,
        result: SummaryResult,
        output_dir: Optional[Path] = None,
        filename_prefix: Optional[str] = None
    ) -> Path:
        """
        Save summary result to file

        Args:
            result: SummaryResult object
            output_dir: Output directory (uses Config.STAGE2_DIR if not provided)
            filename_prefix: Optional prefix for output filename

        Returns:
            Path to saved file
        """
        output_dir = output_dir or Config.STAGE2_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = filename_prefix or result.certificate_type
        base_name = f"{prefix}_{timestamp}"

        # Save summary table (markdown)
        md_file = output_dir / f"{base_name}_summary.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {result.certificate_type.upper()} Certificate Summary\n\n")
            f.write(f"**Generated:** {result.processing_timestamp}\n\n")
            f.write(f"**Documents Processed:** {result.document_count}\n\n")
            f.write("---\n\n")
            f.write(result.summary_table)

        # Save metadata as JSON
        json_file = output_dir / f"{base_name}_metadata.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(result.to_json())

        logger.info(f"Summary result saved: {md_file.name}")
        return md_file

    def validate_summary(
        self,
        result: SummaryResult,
        cert_type: CertificateType
    ) -> Dict[str, any]:
        """
        Validate summary result for completeness

        Args:
            result: SummaryResult object
            cert_type: Certificate type

        Returns:
            Validation report dictionary
        """
        required_fields = CertificateSpecs.get_summary_fields(cert_type)

        # Check if all required fields are mentioned in summary
        missing_fields = []
        for field in required_fields:
            if field.lower() not in result.summary_table.lower():
                missing_fields.append(field)

        validation_report = {
            "is_valid": len(missing_fields) == 0,
            "total_fields": len(required_fields),
            "missing_fields": missing_fields,
            "missing_count": len(missing_fields)
        }

        if missing_fields:
            logger.warning(
                f"Validation: {len(missing_fields)} fields potentially missing from summary"
            )
        else:
            logger.info("Validation: All required fields found in summary")

        return validation_report
