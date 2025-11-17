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

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    logging.warning("PyPDF2 not installed - PDF page counting disabled")

from config import Config

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
    page_count: Optional[int] = None  # Number of pages (for PDFs)
    is_multi_page: bool = False  # True if PDF has multiple pages
    potential_multi_doc: bool = False  # Warning flag for potential multiple documents

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

    @staticmethod
    def get_pdf_page_count(file_path: Path) -> Optional[int]:
        """
        Get page count from PDF file

        Args:
            file_path: Path to PDF file

        Returns:
            Number of pages, or None if cannot be determined
        """
        if not PDF_SUPPORT:
            logger.warning("PyPDF2 not available - cannot count PDF pages")
            return None

        if not FileHandler.is_pdf(file_path):
            return None

        try:
            reader = PdfReader(str(file_path))
            page_count = len(reader.pages)
            logger.info(f"PDF {file_path.name} has {page_count} page(s)")

            # Log warning for multi-page PDFs
            if page_count > 3:
                logger.warning(
                    f"PDF {file_path.name} has {page_count} pages - "
                    f"may contain multiple documents. Consider splitting or reviewing extraction carefully."
                )
            elif page_count > 1:
                logger.info(
                    f"PDF {file_path.name} has {page_count} pages - "
                    f"verify all pages are processed correctly."
                )

            return page_count
        except Exception as e:
            logger.error(f"Error reading PDF page count for {file_path.name}: {str(e)}")
            return None

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

        # Get page count for PDFs
        page_count = None
        is_multi_page = False
        potential_multi_doc = False

        if cls.is_pdf(file_path):
            page_count = cls.get_pdf_page_count(file_path)
            if page_count:
                is_multi_page = page_count > 1
                # Warn if PDF has many pages - likely contains multiple documents
                potential_multi_doc = page_count > 3

        metadata = FileMetadata(
            file_path=str(file_path.absolute()),
            file_name=file_path.name,
            file_size=file_stat.st_size,
            file_extension=file_path.suffix.lower(),
            mime_type=mime_type,
            file_hash=cls.calculate_file_hash(file_path),
            upload_timestamp=datetime.now().isoformat(),
            document_id=cls.generate_document_id(file_path),
            page_count=page_count,
            is_multi_page=is_multi_page,
            potential_multi_doc=potential_multi_doc
        )

        logger.info(f"Extracted metadata for: {file_path.name}")
        if is_multi_page:
            logger.info(f"  → Multi-page PDF detected: {page_count} pages")
        if potential_multi_doc:
            logger.warning(f"  ⚠ Potential multiple documents in single PDF!")

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
