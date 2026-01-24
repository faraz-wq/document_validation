import os
import requests
import json
import sys

BASE_URL = "http://localhost:8000"
SAMPLES_DIR = "/home/faraz/workspace/document_validation/samples"

# Mapping folder names to Application Types
APP_TYPE_MAPPING = {
    "Income Certificate": "Income Certificate",
    "Integrated Certificate": "Integrated Certificate",
    "OBC": "OBC Certificate",
    "EWS Certificate": "EWS Certificate",
    "Family Member Certificate": "Family Member Certificate"
}

def run_test_for_sample(category_folder, sample_subfolder):
    app_type = APP_TYPE_MAPPING.get(category_folder)
    if not app_type:
        print(f"Skipping unknown category: {category_folder}")
        return

    sample_path = os.path.join(SAMPLES_DIR, category_folder, sample_subfolder)
    if not os.path.isdir(sample_path):
        return

    print(f"\nTesting {category_folder} - {sample_subfolder}...")
    
    files_to_upload = []
    opened_files = []
    
    try:
        # Gather all files in the sample directory
        for filename in os.listdir(sample_path):
            file_path = os.path.join(sample_path, filename)
            if os.path.isfile(file_path):
                # We need to keep files open until request is sent
                f = open(file_path, 'rb')
                opened_files.append(f)
                files_to_upload.append(('files', (filename, f, 'application/octet-stream')))

        if not files_to_upload:
            print("No files found in sample folder.")
            return

        payload = {'application_type': app_type}
        
        try:
            response = requests.post(f"{BASE_URL}/extract-summary", data=payload, files=files_to_upload)
            
            if response.status_code == 200:
                print("✅ Success!")
                print(json.dumps(response.json(), indent=2))
            else:
                print(f"❌ Failed with status {response.status_code}")
                print(response.text)
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to server. Is it running?")
            sys.exit(1)

    finally:
        # Close all file handles
        for f in opened_files:
            f.close()

def main():
    # Test one sample from each category to verify
    categories = [d for d in os.listdir(SAMPLES_DIR) if os.path.isdir(os.path.join(SAMPLES_DIR, d))]
    
    for category in categories:
        if category not in APP_TYPE_MAPPING:
            continue
            
        category_path = os.path.join(SAMPLES_DIR, category)
        samples = sorted([d for d in os.listdir(category_path) if os.path.isdir(os.path.join(category_path, d))])
        
        if samples:
            # Run for the first sample found in this category
            run_test_for_sample(category, samples[0])
        else:
            print(f"No samples found in {category}")

if __name__ == "__main__":
    main()
