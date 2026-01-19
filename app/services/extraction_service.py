from typing import List, Dict, Any, Optional
from fastapi import UploadFile
from app.verification.processor import VerificationProcessor
from app.verification.schema import VerificationConfig
from app.utils.pdf_utils import combine_pdf_and_non_pdf_files
from app.api.v1 import sessions as v1_sessions
from app.logging_config import get_logger

logger = get_logger(__name__)

class ExtractionService:
    """
    Service responsible for document extraction and session management.
    """
    def __init__(self):
        self.processor = VerificationProcessor()

    async def extract_from_upload_files(
        self, 
        application_type: str, 
        files: List[UploadFile], 
        config: VerificationConfig,
        combine_pdfs: bool = True,
        user_id: Optional[int] = None,
        api_key_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Processes a list of UploadFile objects, performs extraction, and saves the session.
        Now includes file validation to prevent memory and security issues.
        """
        logger.info(f"Extracting from {len(files)} files for {application_type}")
        
        # 0. Validate files before processing
        from app.utils.file_validator import file_validator
        file_validator.validate_files(files)
        
        # 1. Read files into memory
        file_data_list = []
        for file in files:
            content = await file.read()
            
            # Additional validation after reading content
            file_validator.validate_file_content(content, file.filename)
            
            file_data_list.append({
                "filename": file.filename,
                "content": content,
                "mime_type": file.content_type
            })
            await file.seek(0)

        # 2. Combine PDFs if requested
        if combine_pdfs:
            file_data_list = combine_pdf_and_non_pdf_files(file_data_list)

        # 3. Perform Agnostic Extraction
        try:
            result = self.processor.process(application_type, file_data_list, config)
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            raise Exception(f"AI Extraction failed: {str(e)}")

        # 4. Create Database Session (Persistence)
        try:
            session_id = v1_sessions.create_session(
                application_type=application_type,
                summary=result.copy(),
                files=file_data_list,
                user_id=user_id,
                api_key_id=api_key_id
            )
            result['session_id'] = session_id
        except Exception as db_error:
            logger.error(f"Failed to create extraction session in DB: {db_error}")

        return result

# Singleton instance
_extraction_service = None

def get_extraction_service() -> ExtractionService:
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service
