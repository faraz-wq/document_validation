from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from typing import List, Annotated
import uvicorn
import logging
from app.logging_config import setup_logging, get_logger
from app.extractor import GeminiExtractor, ExtractionError
from app.models import (
    IntegratedCertificateSummary,
    IncomeCertificateSummary,
    OBCCertificateSummary,
    EWSCertificateSummary,
    FamilyMemberCertificateSummary
)

# Setup logging
setup_logging(log_level="DEBUG", log_file="logs/app.log")
logger = get_logger(__name__)

app = FastAPI(title="Document Validation Service")
logger.info("Document Validation Service initialized")

extractor = GeminiExtractor()
logger.info("GeminiExtractor initialized")

@app.post("/extract-summary")
async def extract_summary(
    application_type: Annotated[str, Form(..., description="Type of application service")],
    files: List[UploadFile] = File(..., description="List of document files")
):
    """
    Extracts structured summary from uploaded documents based on the application type.
    """
    logger.info(f"Received extraction request for application type: {application_type}")
    logger.info(f"Number of files received: {len(files)}")

    # Log details about each file
    for i, file in enumerate(files):
        logger.debug(f"File {i+1}: {file.filename}, size: {file.size}, content_type: {file.content_type}")

    # Read files into memory (be mindful of large files in production)
    file_data_list = []
    for file in files:
        logger.debug(f"Reading file content for: {file.filename}")
        content = await file.read()
        logger.info(f"Successfully read file: {file.filename}, size: {len(content)} bytes")

        file_data_list.append({
            "filename": file.filename,
            "content": content,
            "mime_type": file.content_type
        })

    try:
        logger.info(f"Starting extraction for application type: {application_type}")
        result = extractor.extract(application_type, file_data_list)
        logger.info(f"Extraction completed successfully for application type: {application_type}")
        return result
    except ExtractionError as e:
        logger.error(f"ExtractionError in extract_summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in extract_summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated")

if __name__ == "__main__":
    logger.info("Starting Document Validation Service on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
