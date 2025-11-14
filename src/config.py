"""
Configuration module for Document Validation Workflow
Handles Gemini API configuration and application settings
"""

import os
from pathlib import Path
from typing import Optional

class Config:
    """Configuration class for the document validation system"""

    # API Configuration
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Generation Configuration
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.1"))
    TOP_P: float = float(os.getenv("TOP_P", "0.95"))
    TOP_K: int = int(os.getenv("TOP_K", "40"))
    MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "8192"))

    # File Configuration
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png']
    SUPPORTED_PDF_FORMATS = ['.pdf']
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "20"))

    # Directory Configuration
    BASE_DIR = Path(__file__).parent.parent
    OUTPUTS_DIR = BASE_DIR / "outputs"
    STAGE1_DIR = OUTPUTS_DIR / "stage1_extractions"
    STAGE2_DIR = OUTPUTS_DIR / "stage2_summaries"

    # API Retry Configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY: float = float(os.getenv("RETRY_DELAY", "2.0"))
    RETRY_BACKOFF: float = float(os.getenv("RETRY_BACKOFF", "2.0"))

    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "document_validation.log")

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment."
            )
        return True

    @classmethod
    def get_supported_formats(cls) -> list[str]:
        """Get list of all supported file formats"""
        return cls.SUPPORTED_IMAGE_FORMATS + cls.SUPPORTED_PDF_FORMATS
