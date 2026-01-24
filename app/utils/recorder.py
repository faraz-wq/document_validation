import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Base directory for all records
RECORDS_BASE_DIR = Path("records")

def save_record(category: str, data: Any, filename_prefix: str = "record"):
    """
    Saves data to a JSON file in a categorized directory under 'records/'.
    
    Args:
        category: Subdirectory name (e.g., 'ocr', 'gemini_raw', 'gemini_processed')
        data: The data to save (must be JSON serializable)
        filename_prefix: Prefix for the filename
    """
    try:
        # Ensure base directories exist
        category_dir = RECORDS_BASE_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{filename_prefix}_{timestamp}.json"
        filepath = category_dir / filename
        
        # Handle cases where data might not be a dict (e.g. raw string from LLM)
        if not isinstance(data, (dict, list)):
            data = {"raw_output": str(data)}
            
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        return str(filepath)
    except Exception as e:
        # We don't want recording failures to crash the main process
        print(f"Error saving record for {category}: {e}")
        return None
