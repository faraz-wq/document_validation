"""
Evaluation Script
Run metrics evaluation on test dataset with ground truth annotations
"""

import sys
import argparse
import json
import logging
from pathlib import Path
from typing import List, Dict
import time

from config import Config
from certificate_types import CertificateSpecs
from main import DocumentValidationWorkflow
from metrics import (
    DocumentEvaluator,
    MetricsReporter,
    DocumentMetrics,
    SummaryMetrics
)
from utils import setup_logging, print_banner, print_section, print_key_value

logger = logging.getLogger(__name__)


class SystemEvaluator:
    """Evaluate the complete document validation system"""

    def __init__(self, ground_truth_path: Path, documents_dir: Path):
        """
        Initialize system evaluator

        Args:
            ground_truth_path: Path to ground truth JSON file
            documents_dir: Directory containing test documents
        """
        self.ground_truth_path = ground_truth_path
        self.documents_dir = documents_dir
        self.evaluator = DocumentEvaluator(ground_truth_path)
        self.workflow = DocumentValidationWorkflow()

        # Load ground truth
        with open(ground_truth_path, 'r', encoding='utf-8') as f:
            self.ground_truth_data = json.load(f)

        # Support both single object and array
        if isinstance(self.ground_truth_data, dict):
            self.ground_truth_data = [self.ground_truth_data]

        logger.info(f"Loaded {len(self.ground_truth_data)} test cases")

    def evaluate_all(self, save_outputs: bool = True) -> Dict:
        """
        Evaluate all test cases

        Args:
            save_outputs: Whether to save processing outputs

        Returns:
            Complete evaluation results
        """
        print_banner("SYSTEM EVALUATION")
        print_key_value("Test Cases", len(self.ground_truth_data))
        print_key_value("Documents Directory", self.documents_dir)
        print()

        all_document_metrics = []
        all_summary_metrics = []
        failed_cases = []

        for idx, test_case in enumerate(self.ground_truth_data, 1):
            print_section(f"Test Case {idx}/{len(self.ground_truth_data)}: {test_case['document_id']}")

            try:
                doc_metrics, summary_metric = self.evaluate_single_case(
                    test_case,
                    save_outputs
                )

                all_document_metrics.extend(doc_metrics)
                if summary_metric:
                    all_summary_metrics.append(summary_metric)

                print("✓ Test case completed successfully\n")

            except Exception as e:
                logger.error(f"Failed to evaluate test case {test_case['document_id']}: {str(e)}")
                failed_cases.append({
                    'document_id': test_case['document_id'],
                    'error': str(e)
                })
                print(f"❌ Test case failed: {str(e)}\n")

        # Generate overall report
        print_section("EVALUATION RESULTS")

        if all_document_metrics:
            report = MetricsReporter.generate_report(
                document_metrics=all_document_metrics,
                summary_metrics=all_summary_metrics[0] if all_summary_metrics else None,
                output_path=Config.OUTPUTS_DIR / "evaluation_report.txt"
            )
            print(report)

        # Summary statistics
        print("\n" + "=" * 80)
        print("EVALUATION SUMMARY")
        print("=" * 80)
        print_key_value("Total Test Cases", len(self.ground_truth_data))
        print_key_value("Successful", len(self.ground_truth_data) - len(failed_cases))
        print_key_value("Failed", len(failed_cases))

        if failed_cases:
            print("\nFailed Cases:")
            for case in failed_cases:
                print(f"  • {case['document_id']}: {case['error']}")

        # Calculate aggregate metrics
        results = {
            "total_cases": len(self.ground_truth_data),
            "successful_cases": len(self.ground_truth_data) - len(failed_cases),
            "failed_cases": len(failed_cases),
            "document_metrics": all_document_metrics,
            "summary_metrics": all_summary_metrics,
            "failed_case_details": failed_cases
        }

        # Save results as JSON
        results_path = Config.OUTPUTS_DIR / "evaluation_results.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            # Convert dataclass objects to dicts for JSON serialization
            json_results = {
                "total_cases": results["total_cases"],
                "successful_cases": results["successful_cases"],
                "failed_cases": results["failed_cases"],
                "document_metrics": [
                    {
                        "document_id": m.document_id,
                        "extraction_rate": m.extraction_rate,
                        "field_accuracy": m.field_accuracy,
                        "character_error_rate": m.character_error_rate,
                        "word_error_rate": m.word_error_rate,
                        "processing_time": m.processing_time
                    }
                    for m in all_document_metrics
                ],
                "summary_metrics": [
                    {
                        "summary_id": m.summary_id,
                        "completeness": m.completeness,
                        "value_accuracy": m.value_accuracy,
                        "source_accuracy": m.source_accuracy
                    }
                    for m in all_summary_metrics
                ],
                "failed_case_details": results["failed_case_details"]
            }
            json.dump(json_results, f, indent=2)

        print(f"\nResults saved to: {results_path}")

        return results

    def evaluate_single_case(
        self,
        test_case: Dict,
        save_outputs: bool
    ) -> tuple:
        """
        Evaluate a single test case

        Args:
            test_case: Test case dictionary with ground truth
            save_outputs: Whether to save outputs

        Returns:
            Tuple of (document_metrics_list, summary_metrics)
        """
        document_id = test_case['document_id']
        cert_type = CertificateSpecs.from_string(test_case['certificate_type'])

        # Collect file paths
        file_paths = []
        for doc in test_case['documents']:
            file_path = self.documents_dir / doc['file_name']
            if not file_path.exists():
                raise FileNotFoundError(f"Document not found: {file_path}")
            file_paths.append(file_path)

        print(f"Processing {len(file_paths)} documents...")

        # Run workflow
        start_time = time.time()
        workflow_result = self.workflow.run_complete_workflow(
            file_paths=file_paths,
            cert_type=cert_type,
            save_intermediate=save_outputs
        )
        total_time = time.time() - start_time

        if not workflow_result['success']:
            raise Exception("Workflow execution failed")

        # Evaluate each document
        document_metrics = []
        for idx, doc_result in enumerate(workflow_result['stage1_results']):
            if not doc_result.success:
                continue

            # Get ground truth for this document
            gt_doc = test_case['documents'][idx]
            gt_doc_id = f"{document_id}_{gt_doc['file_name']}"

            # Add to evaluator's ground truth temporarily
            self.evaluator.ground_truth[gt_doc_id] = gt_doc

            # Evaluate
            metrics = self.evaluator.evaluate_document(
                document_id=gt_doc_id,
                extraction_text=doc_result.extracted_text,
                processing_time=doc_result.processing_timestamp
            )

            if metrics:
                document_metrics.append(metrics)
                print(f"  ✓ {doc_result.file_name}: "
                      f"Extraction={metrics.extraction_rate:.1%}, "
                      f"Accuracy={metrics.field_accuracy:.1%}")

        # Evaluate summary
        summary_metrics = None
        if workflow_result['stage2_result'] and workflow_result['stage2_result'].success:
            if 'expected_summary' in test_case:
                summary_metrics = self.evaluator.evaluate_summary(
                    summary_table=workflow_result['stage2_result'].summary_table,
                    expected_summary=test_case['expected_summary'],
                    summary_id=document_id
                )

                print(f"\n  Summary Metrics:")
                print(f"    Completeness: {summary_metrics.completeness:.1%}")
                print(f"    Value Accuracy: {summary_metrics.value_accuracy:.1%}")
                print(f"    Source Accuracy: {summary_metrics.source_accuracy:.1%}")

        return document_metrics, summary_metrics


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Evaluate Document Validation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Evaluate using default paths
  python evaluate.py

  # Evaluate with custom paths
  python evaluate.py --ground-truth ../tests/my_ground_truth.json --documents ../tests/my_docs/

  # Evaluate without saving outputs
  python evaluate.py --no-save-outputs
        """
    )

    parser.add_argument(
        '--ground-truth',
        type=str,
        default='../tests/ground_truth_example.json',
        help='Path to ground truth JSON file'
    )

    parser.add_argument(
        '--documents',
        type=str,
        default='../tests/sample_documents/',
        help='Directory containing test documents'
    )

    parser.add_argument(
        '--no-save-outputs',
        action='store_true',
        help='Do not save processing outputs'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()

    # Setup logging
    setup_logging(log_level=args.log_level, log_to_console=True)

    try:
        # Validate configuration
        Config.validate()

        # Prepare paths
        ground_truth_path = Path(args.ground_truth)
        documents_dir = Path(args.documents)

        if not ground_truth_path.exists():
            print(f"❌ Ground truth file not found: {ground_truth_path}")
            sys.exit(1)

        if not documents_dir.exists():
            print(f"❌ Documents directory not found: {documents_dir}")
            sys.exit(1)

        # Run evaluation
        evaluator = SystemEvaluator(ground_truth_path, documents_dir)
        results = evaluator.evaluate_all(save_outputs=not args.no_save_outputs)

        # Exit with appropriate code
        success_rate = results['successful_cases'] / results['total_cases']
        sys.exit(0 if success_rate >= 0.8 else 1)  # 80% success threshold

    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.exception("Fatal error in evaluation")
        print(f"\n❌ Fatal Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
