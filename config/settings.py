"""
Configuration settings for the document validation pipeline.

Loads environment variables and provides configuration constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# ============================================
# LLM Configuration (REQUIRED)
# ============================================

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
LLM_API_KEY = os.getenv("LLM_API_KEY")

# Validate required LLM configuration
if not LLM_API_KEY:
    raise ValueError(
        "LLM_API_KEY environment variable is required. "
        "Please set it in your .env file or environment."
    )

# ============================================
# Database Configuration (OPTIONAL)
# ============================================

# Leave empty to use JSON file storage
# PostgreSQL: postgresql://user:password@localhost:5432/dbname
# MongoDB: mongodb://localhost:27017/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "")

# ============================================
# Review API Configuration
# ============================================

REVIEW_API_PORT = int(os.getenv("REVIEW_API_PORT", "8000"))

# ============================================
# Processing Configuration
# ============================================

# Maximum number of pages to process in parallel
MAX_PARALLEL_PAGES = int(os.getenv("MAX_PARALLEL_PAGES", "4"))

# Maximum PDF file size in MB
MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "50"))

# Image DPI for PDF rendering
PDF_RENDER_DPI = int(os.getenv("PDF_RENDER_DPI", "300"))

# Confidence threshold for human review (0.0-1.0)
REVIEW_CONFIDENCE_THRESHOLD = float(os.getenv("REVIEW_CONFIDENCE_THRESHOLD", "0.9"))

# ============================================
# Storage Paths
# ============================================

# Output directories
OUTPUT_DIR = project_root / "outputs"
DOCUMENTS_DIR = OUTPUT_DIR / "documents"
PDFS_DIR = OUTPUT_DIR / "pdfs"
RAW_PAGES_DIR = OUTPUT_DIR / "raw_pages"
AGGREGATED_DIR = OUTPUT_DIR / "aggregated"

# Create output directories if they don't exist
for directory in [OUTPUT_DIR, DOCUMENTS_DIR, PDFS_DIR, RAW_PAGES_DIR, AGGREGATED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================
# Logging Configuration
# ============================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ============================================
# Prompt Paths
# ============================================

PROMPTS_DIR = project_root / "prompts"
PAGE_EXTRACTION_PROMPT_PATH = PROMPTS_DIR / "page_extraction.txt"
AGGREGATION_PROMPT_PATH = PROMPTS_DIR / "aggregation.txt"


def get_page_extraction_prompt() -> str:
    """Load page extraction prompt from file."""
    with open(PAGE_EXTRACTION_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


def get_aggregation_prompt() -> str:
    """Load aggregation prompt from file."""
    with open(AGGREGATION_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()


# ============================================
# Configuration Summary
# ============================================

def print_config_summary():
    """Print configuration summary for debugging."""
    print("=" * 60)
    print("Document Validation Pipeline - Configuration")
    print("=" * 60)
    print(f"LLM Base URL: {LLM_BASE_URL}")
    print(f"LLM Model: {LLM_MODEL}")
    print(f"LLM API Key: {'*' * 10}{LLM_API_KEY[-4:] if LLM_API_KEY else 'NOT SET'}")
    print(f"Database URL: {DATABASE_URL if DATABASE_URL else 'JSON file storage'}")
    print(f"Review API Port: {REVIEW_API_PORT}")
    print(f"Max Parallel Pages: {MAX_PARALLEL_PAGES}")
    print(f"Max PDF Size: {MAX_PDF_SIZE_MB} MB")
    print(f"PDF Render DPI: {PDF_RENDER_DPI}")
    print(f"Review Confidence Threshold: {REVIEW_CONFIDENCE_THRESHOLD}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print(f"Log Level: {LOG_LEVEL}")
    print("=" * 60)


if __name__ == "__main__":
    # Print config when run directly
    print_config_summary()
