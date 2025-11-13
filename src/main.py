"""
Main Entry Point for Document Validation Workflow
Orchestrates the complete two-stage document processing pipeline
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional

from config import Config
from certificate_types import CertificateType, CertificateSpecs
from gemini_client import GeminiClient
from document_processor import DocumentProcessor
from summary_generator import SummaryGenerator
from file_handler import FileHandler
from utils import (
    setup_logging,
    print_banner,
    print_section,
    print_subsection,
    print_key_value,
    print_list,
    ProgressTracker
)

logger = logging.getLogger(__name__)

class DocumentValidationWorkflow:
    """Main workflow orchestrator for document validation"""

    def __init__(self):
        """Initialize workflow components"""
        # Validate configuration
        Config.validate()

        # Initialize components
        self.gemini_client = GeminiClient()
        self.document_processor = DocumentProcessor(self.gemini_client)
        self.summary_generator = SummaryGenerator(self.gemini_client)

        logger.info("DocumentValidationWorkflow initialized")

    def run_complete_workflow(
        self,
        file_paths: List[Path],
        cert_type: CertificateType,
        document_names: Optional[List[str]] = None,
        save_intermediate: bool = True
    ) -> dict:
        """
        Run complete two-stage workflow

        Args:
            file_paths: List of document file paths
            cert_type: Certificate type
            document_names: Optional custom document names
            save_intermediate: Whether to save Stage 1 results

        Returns:
            Dictionary with complete workflow results
        """
        print_banner("AP SEVA DOCUMENT VALIDATION WORKFLOW")
        print_key_value("Certificate Type", CertificateSpecs.get_spec(cert_type)["name"])
        print_key_value("Documents to Process", len(file_paths))
        print()

        # Stage 1: Process individual documents
        print_section("STAGE 1: Document Digitization")
        print("Processing documents with Gemini API...")
        print()

        stage1_results = self.run_stage1(
            file_paths=file_paths,
            document_names=document_names,
            save_results=save_intermediate
        )

        # Check for failures
        failed_docs = [r for r in stage1_results if not r.success]
        if failed_docs:
            print(f"\n⚠ Warning: {len(failed_docs)} document(s) failed to process")
            for result in failed_docs:
                print(f"  • {result.file_name}: {result.error_message}")

        successful_docs = [r for r in stage1_results if r.success]
        if not successful_docs:
            print("\n❌ Error: No documents were successfully processed")
            return {
                "success": False,
                "stage1_results": stage1_results,
                "stage2_result": None,
                "error": "All documents failed to process"
            }

        print(f"\n✓ Stage 1 Complete: {len(successful_docs)}/{len(file_paths)} documents processed")

        # Stage 2: Generate cross-document summary
        print_section("STAGE 2: Cross-Document Summary Generation")
        print("Generating consolidated summary...")
        print()

        stage2_result = self.run_stage2(
            extraction_results=successful_docs,
            cert_type=cert_type,
            save_result=True
        )

        if stage2_result.success:
            print("✓ Stage 2 Complete: Summary generated successfully")
        else:
            print(f"❌ Stage 2 Failed: {stage2_result.error_message}")

        # Display summary
        print_section("WORKFLOW SUMMARY")
        print_key_value("Total Documents", len(file_paths))
        print_key_value("Successfully Processed", len(successful_docs))
        print_key_value("Failed", len(failed_docs))
        print_key_value("Certificate Type", cert_type.value)
        print_key_value("Summary Generated", "Yes" if stage2_result.success else "No")
        print()

        if save_intermediate:
            print("Output Locations:")
            print_key_value("  Stage 1 Extractions", Config.STAGE1_DIR, indent=1)
            print_key_value("  Stage 2 Summaries", Config.STAGE2_DIR, indent=1)
            print()

        return {
            "success": stage2_result.success and len(successful_docs) > 0,
            "stage1_results": stage1_results,
            "stage2_result": stage2_result,
            "certificate_type": cert_type.value,
            "documents_processed": len(successful_docs),
            "documents_failed": len(failed_docs)
        }

    def run_stage1(
        self,
        file_paths: List[Path],
        document_names: Optional[List[str]] = None,
        save_results: bool = True
    ) -> List:
        """
        Run Stage 1: Individual document processing

        Args:
            file_paths: List of document file paths
            document_names: Optional custom document names
            save_results: Whether to save results

        Returns:
            List of DocumentExtractionResult objects
        """
        results = []
        progress = ProgressTracker(len(file_paths), "Stage 1 Progress")

        for idx, file_path in enumerate(file_paths):
            doc_name = None
            if document_names and idx < len(document_names):
                doc_name = document_names[idx]

            result = self.document_processor.process_document(file_path, doc_name)
            results.append(result)

            if save_results and result.success:
                self.document_processor.save_extraction_result(result)

            progress.update()

        progress.complete()
        return results

    def run_stage2(
        self,
        extraction_results: List,
        cert_type: CertificateType,
        save_result: bool = True
    ):
        """
        Run Stage 2: Summary generation

        Args:
            extraction_results: List of Stage 1 results
            cert_type: Certificate type
            save_result: Whether to save result

        Returns:
            SummaryResult object
        """
        result = self.summary_generator.generate_summary(
            extraction_results=extraction_results,
            cert_type=cert_type
        )

        if save_result and result.success:
            self.summary_generator.save_summary_result(result)

        return result

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="AP Seva Document Validation Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process integrated certificate documents
  python main.py --cert-type integrated --files doc1.pdf doc2.jpg doc3.pdf

  # Process income certificate with custom names
  python main.py --cert-type income --files app.pdf ration.jpg --names "Application Form" "Ration Card"

  # Process with custom output directory
  python main.py --cert-type ews --files *.pdf --output ./my_output
        """
    )

    parser.add_argument(
        '--files',
        nargs='+',
        required=True,
        help='Paths to document files (PDFs and images)'
    )

    parser.add_argument(
        '--cert-type',
        required=True,
        choices=CertificateSpecs.get_certificate_types(),
        help='Type of certificate application'
    )

    parser.add_argument(
        '--names',
        nargs='+',
        help='Optional custom names for documents (must match number of files)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Custom output directory'
    )

    parser.add_argument(
        '--no-save-stage1',
        action='store_true',
        help='Do not save Stage 1 intermediate results'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    parser.add_argument(
        '--log-file',
        type=str,
        help='Path to log file'
    )

    return parser.parse_args()

def main():
    """Main entry point"""
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(
        log_level=args.log_level,
        log_file=args.log_file,
        log_to_console=True
    )

    try:
        # Validate and prepare file paths
        file_paths = [Path(f) for f in args.files]

        # Validate all files
        print("Validating files...")
        for file_path in file_paths:
            FileHandler.validate_file(file_path)

        # Parse certificate type
        cert_type = CertificateSpecs.from_string(args.cert_type)

        # Validate document names if provided
        document_names = args.names
        if document_names and len(document_names) != len(file_paths):
            print(f"Error: Number of names ({len(document_names)}) must match number of files ({len(file_paths)})")
            sys.exit(1)

        # Update output directories if custom path provided
        if args.output:
            output_path = Path(args.output)
            Config.STAGE1_DIR = output_path / "stage1_extractions"
            Config.STAGE2_DIR = output_path / "stage2_summaries"

        # Create workflow and run
        workflow = DocumentValidationWorkflow()
        result = workflow.run_complete_workflow(
            file_paths=file_paths,
            cert_type=cert_type,
            document_names=document_names,
            save_intermediate=not args.no_save_stage1
        )

        # Exit with appropriate code
        sys.exit(0 if result["success"] else 1)

    except KeyboardInterrupt:
        print("\n\nWorkflow interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.exception("Fatal error in workflow")
        print(f"\n❌ Fatal Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
