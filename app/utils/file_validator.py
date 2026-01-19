"""
File validation utilities for document processing
Provides size and type validation to prevent memory and security issues
"""

import os
from typing import List
from fastapi import HTTPException, UploadFile
from app.logging_config import get_logger

logger = get_logger(__name__)


class FileValidator:
    """Validates uploaded files for size and type constraints"""
    
    def __init__(self):
        # Maximum size for a single file (default: 50MB)
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE_BYTES", str(50 * 1024 * 1024)))
        
        # Maximum total size for all files in a request (default: 100MB)
        self.max_total_size = int(os.getenv("MAX_TOTAL_SIZE_BYTES", str(100 * 1024 * 1024)))
        
        # Allowed MIME types for uploaded files
        self.allowed_mime_types = {
            'application/pdf',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/tiff',
            'image/bmp',
            'image/webp'
        }
        
        logger.info(f"FileValidator initialized: max_file_size={self.max_file_size} bytes, "
                   f"max_total_size={self.max_total_size} bytes")
    
    def validate_files(self, files: List[UploadFile]) -> None:
        """
        Validate a list of uploaded files before processing.
        
        Args:
            files: List of FastAPI UploadFile objects
            
        Raises:
            HTTPException: If validation fails
        """
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=400,
                detail="No files provided"
            )
        
        total_size = 0
        
        for file in files:
            # Check if file has size attribute (some implementations don't)
            if hasattr(file, 'size') and file.size:
                if file.size > self.max_file_size:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File '{file.filename}' exceeds maximum size of {self.max_file_size / (1024 * 1024):.1f}MB"
                    )
                total_size += file.size
            
            # Check MIME type if available
            if file.content_type:
                if file.content_type not in self.allowed_mime_types:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File '{file.filename}' has unsupported MIME type: {file.content_type}. "
                               f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}"
                    )
        
        # Check total size
        if total_size > self.max_total_size:
            raise HTTPException(
                status_code=413,
                detail=f"Total size of all files ({total_size / (1024 * 1024):.1f}MB) exceeds maximum of "
                       f"{self.max_total_size / (1024 * 1024):.1f}MB"
            )
        
        logger.info(f"File validation passed: {len(files)} files, total size: {total_size / (1024 * 1024):.2f}MB")
    
    def validate_file_content(self, content: bytes, filename: str) -> None:
        """
        Validate file content after reading (for streaming scenarios).
        
        Args:
            content: File content as bytes
            filename: Name of the file
            
        Raises:
            HTTPException: If validation fails
        """
        if len(content) > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File '{filename}' content exceeds maximum size of {self.max_file_size / (1024 * 1024):.1f}MB"
            )
        
        logger.debug(f"Content validation passed for '{filename}': {len(content) / (1024 * 1024):.2f}MB")


# Global file validator instance
file_validator = FileValidator()
