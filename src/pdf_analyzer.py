"""
PDF Analysis Utility
Provides tools for analyzing multi-page PDFs and detecting document boundaries
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PyPDF2 not installed - PDF analysis features disabled")

logger = logging.getLogger(__name__)


@dataclass
class PageInfo:
    """Information about a single page in a PDF"""
    page_number: int  # 1-indexed
    text_content: Optional[str] = None
    char_count: int = 0
    has_text: bool = False
    estimated_document_type: Optional[str] = None


@dataclass
class PDFAnalysis:
    """Complete analysis of a PDF file"""
    file_path: str
    total_pages: int
    pages: List[PageInfo]
    potential_document_boundaries: List[int]  # Page numbers where documents might start
    warnings: List[str]


class PDFAnalyzer:
    """Analyze PDF structure and detect potential multiple documents"""

    # Keywords that suggest document types
    DOCUMENT_TYPE_KEYWORDS = {
        "application": ["application form", "application for", "प्रार्थना पत्र"],
        "certificate": ["certificate", "प्रमाण पत्र", "certified", "certification"],
        "ration_card": ["ration card", "राशन कार्ड"],
        "id_proof": ["aadhaar", "aadhar", "आधार", "voter id", "epic"],
        "income_proof": ["income", "salary", "pay slip", "it returns", "आय"],
        "marksheet": ["marks memo", "ssc", "intermediate", "marks card", "अंक पत्र"],
        "caste": ["caste", "जाति", "community", "समुदाय"],
        "death_cert": ["death certificate", "मृत्यु प्रमाण"]
    }

    @staticmethod
    def analyze_pdf(file_path: Path) -> Optional[PDFAnalysis]:
        """
        Analyze PDF file structure

        Args:
            file_path: Path to PDF file

        Returns:
            PDFAnalysis object or None if analysis fails
        """
        if not PDF_SUPPORT:
            logger.error("PyPDF2 not installed - cannot analyze PDF")
            return None

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        try:
            reader = PdfReader(str(file_path))
            total_pages = len(reader.pages)

            logger.info(f"Analyzing PDF: {file_path.name} ({total_pages} pages)")

            pages = []
            warnings = []

            for page_num, page in enumerate(reader.pages, start=1):
                # Extract text from page
                try:
                    text = page.extract_text()
                    char_count = len(text)
                    has_text = char_count > 50  # At least 50 chars to be considered meaningful

                    # Estimate document type
                    doc_type = PDFAnalyzer._estimate_document_type(text)

                    page_info = PageInfo(
                        page_number=page_num,
                        text_content=text[:500] if text else None,  # First 500 chars
                        char_count=char_count,
                        has_text=has_text,
                        estimated_document_type=doc_type
                    )

                    pages.append(page_info)

                    if not has_text:
                        warnings.append(f"Page {page_num} has little to no text (may be blank or image-only)")
                    else:
                        logger.debug(f"  Page {page_num}: {char_count} chars, type: {doc_type or 'unknown'}")

                except Exception as e:
                    logger.error(f"Error extracting text from page {page_num}: {str(e)}")
                    pages.append(PageInfo(page_number=page_num, has_text=False))
                    warnings.append(f"Page {page_num} could not be processed")

            # Detect document boundaries
            boundaries = PDFAnalyzer._detect_document_boundaries(pages)

            # Add warnings for potential multi-document PDF
            if len(boundaries) > 1:
                warnings.append(
                    f"Detected {len(boundaries)} potential documents starting at pages: {boundaries}"
                )

            analysis = PDFAnalysis(
                file_path=str(file_path),
                total_pages=total_pages,
                pages=pages,
                potential_document_boundaries=boundaries,
                warnings=warnings
            )

            logger.info(f"Analysis complete: {total_pages} pages, {len(boundaries)} potential documents")
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze PDF {file_path.name}: {str(e)}")
            return None

    @staticmethod
    def _estimate_document_type(text: str) -> Optional[str]:
        """
        Estimate document type based on text content

        Args:
            text: Text content

        Returns:
            Estimated document type or None
        """
        if not text:
            return None

        text_lower = text.lower()

        # Count keyword matches for each document type
        type_scores = {}
        for doc_type, keywords in PDFAnalyzer.DOCUMENT_TYPE_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text_lower)
            if score > 0:
                type_scores[doc_type] = score

        if not type_scores:
            return None

        # Return type with highest score
        return max(type_scores.items(), key=lambda x: x[1])[0]

    @staticmethod
    def _detect_document_boundaries(pages: List[PageInfo]) -> List[int]:
        """
        Detect potential document boundaries in multi-page PDF

        Args:
            pages: List of PageInfo objects

        Returns:
            List of page numbers where documents might start (1-indexed)
        """
        boundaries = [1]  # First page is always a boundary

        if len(pages) <= 1:
            return boundaries

        prev_type = pages[0].estimated_document_type

        for page in pages[1:]:
            # Boundary if document type changes
            if page.estimated_document_type and page.estimated_document_type != prev_type:
                boundaries.append(page.page_number)
                logger.debug(
                    f"  Boundary detected at page {page.page_number}: "
                    f"{prev_type} → {page.estimated_document_type}"
                )

            prev_type = page.estimated_document_type

        return boundaries

    @staticmethod
    def generate_analysis_report(analysis: PDFAnalysis) -> str:
        """
        Generate human-readable analysis report

        Args:
            analysis: PDFAnalysis object

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"PDF ANALYSIS REPORT: {Path(analysis.file_path).name}")
        lines.append("=" * 80)
        lines.append(f"\nTotal Pages: {analysis.total_pages}")
        lines.append(f"Potential Documents: {len(analysis.potential_document_boundaries)}")

        if analysis.potential_document_boundaries:
            lines.append(f"Document Start Pages: {analysis.potential_document_boundaries}")

        lines.append("\n" + "-" * 80)
        lines.append("PAGE-BY-PAGE ANALYSIS")
        lines.append("-" * 80)

        for page in analysis.pages:
            status = "✓" if page.has_text else "✗"
            doc_type = page.estimated_document_type or "unknown"
            lines.append(
                f"Page {page.page_number:2d}: {status} {page.char_count:5d} chars | Type: {doc_type}"
            )

        if analysis.warnings:
            lines.append("\n" + "-" * 80)
            lines.append("WARNINGS")
            lines.append("-" * 80)
            for warning in analysis.warnings:
                lines.append(f"⚠  {warning}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    @staticmethod
    def save_analysis_report(analysis: PDFAnalysis, output_path: Path) -> None:
        """
        Save analysis report to file

        Args:
            analysis: PDFAnalysis object
            output_path: Path to save report
        """
        report = PDFAnalyzer.generate_analysis_report(analysis)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Analysis report saved to: {output_path}")


def analyze_and_report(pdf_path: Path, output_dir: Optional[Path] = None) -> Optional[PDFAnalysis]:
    """
    Convenience function to analyze PDF and generate report

    Args:
        pdf_path: Path to PDF file
        output_dir: Optional directory to save report

    Returns:
        PDFAnalysis object
    """
    analysis = PDFAnalyzer.analyze_pdf(pdf_path)

    if not analysis:
        return None

    # Print report
    print(PDFAnalyzer.generate_analysis_report(analysis))

    # Save if output directory specified
    if output_dir:
        output_path = output_dir / f"{pdf_path.stem}_analysis.txt"
        PDFAnalyzer.save_analysis_report(analysis, output_path)

    return analysis


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_analyzer.py <path_to_pdf>")
        sys.exit(1)

    pdf_file = Path(sys.argv[1])
    output_directory = Path("outputs") if len(sys.argv) < 3 else Path(sys.argv[2])

    analyze_and_report(pdf_file, output_directory)
