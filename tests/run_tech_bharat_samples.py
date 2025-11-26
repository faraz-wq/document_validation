import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.config import Config
from src.certificate_types import CertificateType
from src.main import DocumentValidationWorkflow

# Load environment variables
load_dotenv()

def get_cert_type_from_dir(dir_name):
    mapping = {
        "Integrated Certificate": CertificateType.INTEGRATED,
        "Income Certificate": CertificateType.INCOME,
        "OBC": CertificateType.OBC,
        "EWS Certificate": CertificateType.EWS,
        "Family Member Certificate": CertificateType.FAMILY_MEMBER
    }
    return mapping.get(dir_name)

def main():
    base_dir = project_root / "tests/sample_documents/Tech Bharat"
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}")
        return

    print(f"Starting validation for samples in: {base_dir}")
    
    # Validate API key
    try:
        Config.validate()
    except Exception as e:
        print(f"Configuration Error: {e}")
        return

    workflow = DocumentValidationWorkflow()
    
    # Iterate through certificate type directories
    for cert_dir in sorted(base_dir.iterdir()):
        if not cert_dir.is_dir():
            continue
            
        cert_type = get_cert_type_from_dir(cert_dir.name)
        if not cert_type:
            print(f"Skipping unknown directory: {cert_dir.name}")
            continue
            
        print(f"\n{'='*50}")
        print(f"Processing Certificate Type: {cert_dir.name} ({cert_type.value})")
        print(f"{'='*50}")
        
        # Iterate through sample directories
        for sample_dir in sorted(cert_dir.iterdir()):
            if not sample_dir.is_dir():
                continue
                
            print(f"\n  Processing Sample: {sample_dir.name}")
            
            file_paths = []
            for file_path in sample_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.jpg', '.jpeg', '.png']:
                    file_paths.append(file_path)
            
            if not file_paths:
                print(f"    No valid files found in {sample_dir.name}")
                continue
                
            print(f"    Found {len(file_paths)} files: {[f.name for f in file_paths]}")
            
            try:
                result = workflow.run_complete_workflow(
                    file_paths=file_paths,
                    cert_type=cert_type,
                    document_names=[f.name for f in file_paths],
                    save_intermediate=True
                )
                
                if result["success"]:
                    print(f"    ✅ Success")
                else:
                    print(f"    ❌ Failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"    ❌ Exception: {str(e)}")

if __name__ == "__main__":
    main()
