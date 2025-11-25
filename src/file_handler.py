"""
File Handler Module
Validates files and manages metadata for document processing
"""

import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from src.config import Config

logger = logging.getLogger(__name__)

@dataclass
class FileMetadata:
    """Metadata for uploaded files"""
    file_path: str
    file_name: str
    file_size: int
    file_extension: str
    mime_type: Optional[str]
    file_hash: str
    upload_timestamp: str
    document_id: str
    page_count: Optional[int] = None  # Added for PDF files

    def to_dict(self) -> Dict:
        """Convert metadata to dictionary"""
        return asdict(self)

class FileHandler:
    """Handles file validation and metadata management"""

    @staticmethod
    def validate_file(file_path: Path) -> bool:
        """
        Validate that file exists, has supported format, and is within size limit

        Args:
            file_path: Path to file

        Returns:
            True if file is valid

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format or size is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Check file extension
        extension = file_path.suffix.lower()
        supported_formats = Config.get_supported_formats()

        if extension not in supported_formats:
            raise ValueError(
                f"Unsupported file format: {extension}. "
                f"Supported formats: {', '.join(supported_formats)}"
            )

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > Config.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"File size ({file_size_mb:.2f} MB) exceeds maximum "
                f"allowed size ({Config.MAX_FILE_SIZE_MB} MB)"
            )

        logger.info(f"File validated: {file_path.name} ({file_size_mb:.2f} MB)")
        return True

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """
        Calculate SHA256 hash of file

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def generate_document_id(file_path: Path) -> str:
        """
        Generate unique document ID based on filename and timestamp

        Args:
            file_path: Path to file

        Returns:
            Unique document ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = file_path.stem.replace(" ", "_")
        return f"{file_stem}_{timestamp}"

    @classmethod
    def get_file_metadata(cls, file_path: Path) -> FileMetadata:
        """
        Extract and generate metadata for a file

        Args:
            file_path: Path to file

        Returns:
            FileMetadata object
        """
        cls.validate_file(file_path)

        file_stat = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        # Determine page count for PDF files
        page_count = None
        if cls.is_pdf(file_path):
            try:
                import PyPDF2
                with open(file_path, 'rb') as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    page_count = len(reader.pages)
            except Exception as e:
                logger.warning(f"Could not determine page count for PDF {file_path.name}: {e}")

        metadata = FileMetadata(
            file_path=str(file_path.absolute()),
            file_name=file_path.name,
            file_size=file_stat.st_size,
            file_extension=file_path.suffix.lower(),
            mime_type=mime_type,
            file_hash=cls.calculate_file_hash(file_path),
            upload_timestamp=datetime.now().isoformat(),
            document_id=cls.generate_document_id(file_path),
            page_count=page_count
        )

        logger.info(f"Extracted metadata for: {file_path.name} (Page count: {page_count})")
        return metadata

    @staticmethod
    def validate_batch(file_paths: List[Path]) -> List[FileMetadata]:
        """
        Validate multiple files and return their metadata

        Args:
            file_paths: List of file paths

        Returns:
            List of FileMetadata objects
        """
        metadata_list = []

        for file_path in file_paths:
            try:
                metadata = FileHandler.get_file_metadata(file_path)
                metadata_list.append(metadata)
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                raise

        logger.info(f"Validated batch of {len(metadata_list)} files")
        return metadata_list

    @staticmethod
    def is_pdf(file_path: Path) -> bool:
        """Check if file is a PDF"""
        return file_path.suffix.lower() in Config.SUPPORTED_PDF_FORMATS

    @staticmethod
    def is_image(file_path: Path) -> bool:
        """Check if file is an image"""
        return file_path.suffix.lower() in Config.SUPPORTED_IMAGE_FORMATS
