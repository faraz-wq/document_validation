from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Annotated
import uvicorn
import logging
import json
import shutil
import os
from pathlib import Path
from app.logging_config import setup_logging, get_logger
from app.extractor import GeminiExtractor, ExtractionError
from app.models import (
    IntegratedCertificateSummary,
    IncomeCertificateSummary,
    OBCCertificateSummary,
    EWSCertificateSummary,
    FamilyMemberCertificateSummary
)

# Setup for UI
app = FastAPI(title="Document Validation Service")
import os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
app.mount("/static", StaticFiles(directory=os.path.join(parent_dir, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(parent_dir, "templates"))

# Setup logging
setup_logging(log_level="DEBUG", log_file="logs/app.log")
logger = get_logger(__name__)

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

        # Store the result in a file
        output_dir = Path("extracted_results")
        output_dir.mkdir(exist_ok=True)

        # Create a unique filename based on application type and first file name
        first_filename = Path(file_data_list[0]["filename"]).stem
        output_filename = f"{application_type.replace(' ', '_')}_{first_filename}_{len(file_data_list)}files.json"
        output_file_path = output_dir / output_filename

        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Results stored in: {output_file_path}")

        return result
    except ExtractionError as e:
        logger.error(f"ExtractionError in extract_summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in extract_summary: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/submit")
async def submit_document(
    request: Request,
    application_type: Annotated[str, Form(..., description="Type of application service")],
    files: List[UploadFile] = File(..., description="List of document files")
):
    """
    Handle form submission, save file, extract data, and render results page.
    """
    logger.info(f"Received submission for: {application_type}")
    
    if not files:
        return templates.TemplateResponse("index.html", {"request": request, "error": "No files uploaded"})

    # Process the first file for preview (current UI limitation, can expand later)
    file = files[0]
    filename = file.filename
    
    # Ensure uploads directory exists
    uploads_dir = Path(parent_dir) / "static" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = uploads_dir / filename
    
    # Save the file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved file to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        return templates.TemplateResponse("index.html", {"request": request, "error": "Failed to save file"})
        
    # Reset file pointer for extraction reading
    # Actually, we saved it, so we can read it back or just use the saved file
    # The extractor expects a list of dicts with 'content' as bytes
    
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            
        file_data_list = [{
            "filename": filename,
            "content": content,
            "mime_type": file.content_type
        }]
        
        logger.info("Starting extraction...")
        result = extractor.extract(application_type, file_data_list)
        
        # Determine file type for the template
        file_type = "pdf" if file.content_type == "application/pdf" else "image"
        file_url = f"/static/uploads/{filename}"
        
        return templates.TemplateResponse(
            "results.html", 
            {
                "request": request, 
                "summary": result, 
                "file_url": file_url, 
                "file_type": file_type,
                "filename": filename
            }
        )
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        return templates.TemplateResponse("index.html", {"request": request, "error": f"Error processing document: {str(e)}"})


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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