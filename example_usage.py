"""
Example usage of the Document Validation Workflow

This script demonstrates how to use the workflow programmatically
(as opposed to using the CLI)
"""

from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import workflow components
from src.config import Config
from src.certificate_types import CertificateType
from src.main import DocumentValidationWorkflow

def example_integrated_certificate():
    """Example: Process an integrated certificate application"""
    print("=" * 80)
    print("Example: Integrated Certificate Processing")
    print("=" * 80)

    # Define your document files
    file_paths = [
        Path("tests/sample_documents/application_form.pdf"),
        Path("tests/sample_documents/caste_certificate.pdf"),
        Path("tests/sample_documents/ration_card.jpg"),
    ]

    # Optional: Provide custom names for better tracking
    document_names = [
        "Application Form",
        "Caste Certificate",
        "Ration Card"
    ]

    # Validate API key is set
    Config.validate()

    # Create workflow instance
    workflow = DocumentValidationWorkflow()

    # Run complete workflow
    result = workflow.run_complete_workflow(
        file_paths=file_paths,
        cert_type=CertificateType.INTEGRATED,
        document_names=document_names,
        save_intermediate=True
    )

    # Check results
    if result["success"]:
        print("\n✓ Workflow completed successfully!")
        print(f"  Processed: {result['documents_processed']} documents")
        print(f"  Failed: {result['documents_failed']} documents")
        print(f"\nOutputs saved to:")
        print(f"  Stage 1: {Config.STAGE1_DIR}")
        print(f"  Stage 2: {Config.STAGE2_DIR}")
    else:
        print("\n❌ Workflow failed")
        if "error" in result:
            print(f"  Error: {result['error']}")

    return result

def example_income_certificate():
    """Example: Process an income certificate application"""
    print("=" * 80)
    print("Example: Income Certificate Processing")
    print("=" * 80)

    file_paths = [
        Path("tests/sample_documents/income_application.pdf"),
        Path("tests/sample_documents/it_returns.pdf"),
        Path("tests/sample_documents/pay_slips.pdf"),
    ]

    document_names = [
        "Application Form",
        "IT Returns",
        "Pay Slips"
    ]

    workflow = DocumentValidationWorkflow()

    result = workflow.run_complete_workflow(
        file_paths=file_paths,
        cert_type=CertificateType.INCOME,
        document_names=document_names,
        save_intermediate=True
    )

    return result

def example_stage_by_stage():
    """Example: Run stages separately for more control"""
    print("=" * 80)
    print("Example: Stage-by-Stage Processing")
    print("=" * 80)

    file_paths = [
        Path("tests/sample_documents/application.pdf"),
        Path("tests/sample_documents/supporting_doc.jpg"),
    ]

    workflow = DocumentValidationWorkflow()

    # Run Stage 1 only
    print("\nRunning Stage 1...")
    stage1_results = workflow.run_stage1(
        file_paths=file_paths,
        save_results=True
    )

    print(f"Stage 1 complete: {len(stage1_results)} documents processed")

    # Inspect Stage 1 results
    for result in stage1_results:
        if result.success:
            print(f"  ✓ {result.file_name}: {len(result.extracted_text)} chars extracted")
        else:
            print(f"  ❌ {result.file_name}: {result.error_message}")

    # Run Stage 2 only if Stage 1 succeeded
    successful_results = [r for r in stage1_results if r.success]
    if successful_results:
        print("\nRunning Stage 2...")
        stage2_result = workflow.run_stage2(
            extraction_results=successful_results,
            cert_type=CertificateType.OBC,
            save_result=True
        )

        if stage2_result.success:
            print("Stage 2 complete: Summary generated")
            print(f"  Document count: {stage2_result.document_count}")
        else:
            print(f"Stage 2 failed: {stage2_result.error_message}")

def example_batch_processing():
    """Example: Process multiple applications in batch"""
    print("=" * 80)
    print("Example: Batch Processing Multiple Applications")
    print("=" * 80)

    applications = [
        {
            "name": "Application 1",
            "cert_type": CertificateType.INTEGRATED,
            "files": [
                Path("tests/sample_documents/app1_form.pdf"),
                Path("tests/sample_documents/app1_caste.pdf"),
            ]
        },
        {
            "name": "Application 2",
            "cert_type": CertificateType.INCOME,
            "files": [
                Path("tests/sample_documents/app2_form.pdf"),
                Path("tests/sample_documents/app2_income.pdf"),
            ]
        },
    ]

    workflow = DocumentValidationWorkflow()
    results = []

    for app in applications:
        print(f"\nProcessing {app['name']}...")
        result = workflow.run_complete_workflow(
            file_paths=app["files"],
            cert_type=app["cert_type"],
            save_intermediate=True
        )
        results.append(result)

    # Summary
    print("\n" + "=" * 80)
    print("Batch Processing Summary")
    print("=" * 80)
    successful = sum(1 for r in results if r["success"])
    print(f"Total applications: {len(applications)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(applications) - successful}")

def main():
    """Main function to run examples"""
    print("\n" + "=" * 80)
    print("AP Seva Document Validation Workflow - Examples")
    print("=" * 80)
    print("\nIMPORTANT: Before running these examples:")
    print("1. Set your GEMINI_API_KEY in the .env file")
    print("2. Place sample documents in tests/sample_documents/")
    print("3. Update file paths in this script to match your documents")
    print("\n" + "=" * 80)

    try:
        # Uncomment the example you want to run:

        # example_integrated_certificate()
        # example_income_certificate()
        # example_stage_by_stage()
        # example_batch_processing()

        print("\nℹ️  Uncomment an example function in main() to run it")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("\nMake sure you have:")
        print("  1. Set GEMINI_API_KEY in .env")
        print("  2. Installed dependencies: pip install -r requirements.txt")
        print("  3. Placed sample documents in the correct paths")

if __name__ == "__main__":
    main()
