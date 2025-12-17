from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Annotated, Optional
import uvicorn
import logging
import json
import shutil
import os
import csv
from datetime import datetime
import sqlite3
from pathlib import Path
from pydantic import BaseModel
from app.logging_config import setup_logging, get_logger
from app.extractor import GeminiExtractor, ExtractionError
from app.database import db
from app.pdf_annotator import annotate_document
from app.models import (
    IntegratedCertificateSummary,
    IncomeCertificateSummary,
    OBCCertificateSummary,
    EWSCertificateSummary,
    FamilyMemberCertificateSummary
)
from app.schemas.schema_models import SchemaDefinition
from app.core.configurable_extractor import ConfigurableExtractor
from app.utils.auth import get_user_from_api_key
from app.db.models import User

# Setup for UI
app = FastAPI(title="Document Validation Service")
 
from fastapi.middleware.cors import CORSMiddleware
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://data-extraction-hub.vercel.app", "http://localhost:3000", "http://localhost:8080"],  # For development convenience, allow all. In prod, specify domains.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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

        # Store the result in a file (for backward compatibility)
        output_dir = Path("extracted_results")
        output_dir.mkdir(exist_ok=True)

        # Create a unique filename based on application type and first file name
        first_filename = Path(file_data_list[0]["filename"]).stem
        output_filename = f"{application_type.replace(' ', '_')}_{first_filename}_{len(file_data_list)}files.json"
        output_file_path = output_dir / output_filename

        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Results stored in: {output_file_path}")
        
        # Annotate documents with bounding boxes
        annotated_files = []
        if result.get('bounding_boxes'):
            logger.info("Annotating documents with bounding boxes")
            
            # Create directories for uploaded and annotated files
            uploads_dir = Path(parent_dir) / "static" / "uploads"
            annotated_dir = Path(parent_dir) / "static" / "annotated"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            annotated_dir.mkdir(parents=True, exist_ok=True)
            
            for file_data in file_data_list:
                filename = file_data['filename']
                content = file_data['content']
                
                # Save the original file temporarily
                file_path = uploads_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(content)
                
                # Filter bounding boxes for this specific file
                file_bounding_boxes = {}
                for field_name, boxes in result['bounding_boxes'].items():
                    # Handle both list and single dict for robustness
                    if isinstance(boxes, dict):
                        boxes = [boxes]
                    
                    if isinstance(boxes, list):
                        # Filter boxes that belong to this file
                        relevant_boxes = [
                            box for box in boxes 
                            if isinstance(box, dict) and box.get('filename') == filename
                        ]
                        if relevant_boxes:
                            file_bounding_boxes[field_name] = relevant_boxes
                
                # Only annotate if there are bounding boxes for this file
                if file_bounding_boxes:
                    try:
                        annotated_path = annotate_document(
                            file_path=file_path,
                            bounding_boxes=file_bounding_boxes,
                            output_dir=annotated_dir,
                            filename_suffix="_annotated"
                        )
                        
                        # Create URL for the annotated file
                        annotated_filename = annotated_path.name
                        annotated_url = f"/static/annotated/{annotated_filename}"
                        annotated_files.append({
                            'original_filename': filename,
                            'annotated_filename': annotated_filename,
                            'annotated_url': annotated_url
                        })
                        
                        logger.info(f"Annotated file saved: {annotated_filename} with {len(file_bounding_boxes)} boxes")
                        
                    except Exception as annot_error:
                        logger.error(f"Failed to annotate {filename}: {annot_error}", exc_info=True)
                        # Continue processing even if annotation fails
                else:
                    logger.info(f"No bounding boxes found for {filename}, skipping annotation")
        
        # Add annotated file URLs to the result
        if annotated_files:
            result['annotated_files'] = annotated_files
        
        # Store in database
        try:
            session_id = v1_sessions.create_session(
                application_type=application_type,
                summary=result.copy(),  # Make a copy since create_session modifies it
                files=file_data_list
            )
            result['session_id'] = session_id
            logger.info(f"Session created with ID: {session_id}")
        except Exception as db_error:
            logger.error(f"Failed to store session in database: {db_error}", exc_info=True)
            # Continue even if database storage fails

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
        
        # Annotate the PDF with bounding boxes if available
        annotated_file_url = None
        if result.get('bounding_boxes'):
            logger.info("Annotating document with bounding boxes")
            
            # Create annotated directory
            annotated_dir = Path(parent_dir) / "static" / "annotated"
            annotated_dir.mkdir(parents=True, exist_ok=True)
            
            # Filter bounding boxes for this specific file
            file_bounding_boxes = {}
            for field_name, boxes in result['bounding_boxes'].items():
                # Handle both list and single dict for robustness
                if isinstance(boxes, dict):
                    boxes = [boxes]
                
                if isinstance(boxes, list):
                    # Filter boxes that belong to this file
                    relevant_boxes = [
                        box for box in boxes 
                        if isinstance(box, dict) and box.get('filename') == filename
                    ]
                    if relevant_boxes:
                        file_bounding_boxes[field_name] = relevant_boxes
            
            if file_bounding_boxes:
                try:
                    annotated_path = annotate_document(
                        file_path=file_path,
                        bounding_boxes=file_bounding_boxes,
                        output_dir=annotated_dir,
                        filename_suffix="_annotated"
                    )
                    
                    # Use annotated file URL instead of original
                    annotated_filename = annotated_path.name
                    annotated_file_url = f"/static/annotated/{annotated_filename}"
                    logger.info(f"Annotated file saved: {annotated_filename} with {len(file_bounding_boxes)} boxes")
                    
                except Exception as annot_error:
                    logger.error(f"Failed to annotate {filename}: {annot_error}", exc_info=True)
                    # Fall back to original file if annotation fails
            else:
                logger.info(f"No bounding boxes found for {filename}, using original file")
        
        # Determine file type for the template
        file_type = "pdf" if file.content_type == "application/pdf" else "image"
        # Use annotated file if available, otherwise use original
        file_url = annotated_file_url if annotated_file_url else f"/view-document/{filename}"
        
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


@app.get("/view-document/{filename}")
async def view_document(filename: str):
    file_path = Path(parent_dir) / "static" / "uploads" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    media_type = "application/octet-stream"
    if filename.lower().endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.lower().endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    elif filename.lower().endswith(".png"):
        media_type = "image/png"
        
    return FileResponse(
        path=file_path, 
        media_type=media_type, 
        headers={"Content-Disposition": "inline"}
    )

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
def health_check():
    logger.info("Health check endpoint accessed")
    return {"status": "ok"}

@app.get("/sessions")
def list_sessions(limit: int = 50):
    """List recent sessions"""
    try:
        sessions = db.list_sessions(limit=limit)
        return {"sessions": sessions}
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Retrieve a specific session with all data"""
    try:
        session_data = db.get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}/document/{filename}")
def get_session_document(session_id: str, filename: str):
    """Retrieve a specific document from a session"""
    try:
        # Get the document record from the database using the SQLAlchemy session
        from app.db.database import SessionLocal
        from app.db.models import Document

        db_session = SessionLocal()
        try:
            db_document = db_session.query(Document).filter(
                Document.session_id == session_id,
                Document.filename == filename
            ).first()

            if not db_document:
                raise HTTPException(status_code=404, detail="Document not found")

            # Construct the full file path and read the content
            full_path = Path("data/documents_v1") / db_document.file_path

            if not full_path.exists():
                raise HTTPException(status_code=404, detail="Document file not found")

            # Read the file content
            with open(full_path, 'rb') as f:
                content = f.read()

            # Return the document as a response
            from fastapi.responses import Response
            return Response(
                content=content,
                media_type=db_document.mime_type or 'application/octet-stream',
                headers={"Content-Disposition": f"inline; filename={filename}"}
            )
        finally:
            db_session.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Delete a session"""
    try:
        success = db.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Include v1 auth routes
from app.api.v1 import auth as v1_auth
from app.api.v1 import sessions as v1_sessions
from app.api.v1 import me_api_keys as v1_me_api_keys
from app.api.v1 import me_stats as v1_me_stats
from app.api.v1 import me_logs as v1_me_logs
from app.api.v1 import me_schemas as v1_me_schemas

app.include_router(v1_auth.router, prefix="", tags=["v1-auth"])
app.include_router(v1_sessions.router, prefix="/v1", tags=["v1-sessions"])
app.include_router(v1_me_api_keys.router, prefix="/v1", tags=["v1-me-api-keys"])
app.include_router(v1_me_stats.router, prefix="/v1", tags=["v1-me-stats"])
app.include_router(v1_me_logs.router, prefix="/v1", tags=["v1-me-logs"])
app.include_router(v1_me_schemas.router, tags=["v1-me-schemas"])

# New v1 endpoints for configurable schemas
@app.post("/v1/schemas")
async def create_schema(
    schema_def: SchemaDefinition,
    current_user: User = Depends(get_user_from_api_key)
):
    """Create a new custom schema definition"""
    from app.core.schema_registry import schema_registry

    # Set current user from API key validation
    schema_def.created_by = current_user.id

    success = schema_registry.register_schema(schema_def)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to register schema - ID may already exist")

    return {"message": "Schema created successfully", "schema_id": schema_def.schema_id}


@app.get("/v1/schemas/{schema_id}")
async def get_schema(
    schema_id: str,
    current_user: User = Depends(get_user_from_api_key)
):
    """Get a specific schema definition"""
    from app.core.schema_registry import schema_registry

    user_id = current_user.id
    schema = schema_registry.get_schema(schema_id, user_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found or access denied")

    return schema


@app.get("/v1/schemas")
async def list_schemas(
    current_user: User = Depends(get_user_from_api_key)
):
    """List all schemas accessible to the user"""
    from app.core.schema_registry import schema_registry

    user_id = current_user.id
    schemas = schema_registry.list_user_schemas(user_id)
    return {"schemas": schemas}


@app.put("/v1/schemas/{schema_id}")
async def update_schema(
    schema_id: str,
    updates: dict,
    current_user: User = Depends(get_user_from_api_key)
):
    """Update an existing schema definition"""
    from app.core.schema_registry import schema_registry

    user_id = current_user.id
    success = schema_registry.update_schema(schema_id, user_id, updates)
    if not success:
        raise HTTPException(status_code=403, detail="Access denied or schema not found")

    return {"message": "Schema updated successfully"}


@app.delete("/v1/schemas/{schema_id}")
async def delete_schema(
    schema_id: str,
    current_user: User = Depends(get_user_from_api_key)
):
    """Delete a schema definition"""
    from app.core.schema_registry import schema_registry

    user_id = current_user.id
    success = schema_registry.delete_schema(schema_id, user_id)
    if not success:
        raise HTTPException(status_code=403, detail="Access denied or schema not found")

    return {"message": "Schema deleted successfully"}


@app.post("/v1/extract-custom")
async def extract_summary_custom(
    request: Request,
    schema_id: Annotated[str, Form(..., description="ID of the custom schema to use")],
    files: List[UploadFile] = File(..., description="List of document files"),
    current_user: User = Depends(get_user_from_api_key)
):
    """
    Extracts structured summary from uploaded documents using a custom schema.
    """
    from app.core.schema_registry import schema_registry

    user_id = current_user.id
    api_key_id = request.state.api_key_id  # Get the API key ID from request state

    # Validate that user has access to this schema
    schema_def = schema_registry.get_schema(schema_id, user_id)
    if not schema_def:
        raise HTTPException(status_code=403, detail="Access denied to this schema")

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
        # Use the custom schema for extraction
        application_type = f"custom:{schema_id}"  # Special prefix for custom schemas
        from app.core.configurable_extractor import ConfigurableExtractor
        extractor = ConfigurableExtractor(user_id=user_id)
        result = extractor.extract(application_type, file_data_list)

        # Store the result in a file (for backward compatibility)
        output_dir = Path("extracted_results")
        output_dir.mkdir(exist_ok=True)

        # Create a unique filename based on application type and first file name
        first_filename = Path(file_data_list[0]["filename"]).stem
        output_filename = f"custom_{schema_id}_{first_filename}_{len(file_data_list)}files.json"
        output_file_path = output_dir / output_filename

        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Results stored in: {output_file_path}")

        # Annotate documents with bounding boxes
        annotated_files = []
        if result.get('bounding_boxes'):
            logger.info("Annotating documents with bounding boxes")

            # Create directories for uploaded and annotated files
            current_dir = os.path.dirname(__file__)
            parent_dir = os.path.dirname(current_dir)
            uploads_dir = Path(parent_dir) / "static" / "uploads"
            annotated_dir = Path(parent_dir) / "static" / "annotated"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            annotated_dir.mkdir(parents=True, exist_ok=True)

            for file_data in file_data_list:
                filename = file_data['filename']
                content = file_data['content']

                # Save the original file temporarily
                file_path = uploads_dir / filename
                with open(file_path, 'wb') as f:
                    f.write(content)

                # Filter bounding boxes for this specific file
                file_bounding_boxes = {}
                for field_name, boxes in result['bounding_boxes'].items():
                    # Handle both list and single dict for robustness
                    if isinstance(boxes, dict):
                        boxes = [boxes]
                    
                    if isinstance(boxes, list):
                        # Filter boxes that belong to this file
                        relevant_boxes = [
                            box for box in boxes 
                            if isinstance(box, dict) and box.get('filename') == filename
                        ]
                        if relevant_boxes:
                            file_bounding_boxes[field_name] = relevant_boxes

                # Only annotate if there are bounding boxes for this file
                if file_bounding_boxes:
                    try:
                        from app.pdf_annotator import annotate_document
                        annotated_path = annotate_document(
                            file_path=file_path,
                            bounding_boxes=file_bounding_boxes,
                            output_dir=annotated_dir,
                            filename_suffix="_annotated"
                        )

                        # Create URL for the annotated file
                        annotated_filename = annotated_path.name
                        annotated_url = f"/static/annotated/{annotated_filename}"
                        annotated_files.append({
                            'original_filename': filename,
                            'annotated_filename': annotated_filename,
                            'annotated_url': annotated_url
                        })

                        logger.info(f"Annotated file saved: {annotated_filename} with {len(file_bounding_boxes)} boxes")

                    except Exception as annot_error:
                        logger.error(f"Failed to annotate {filename}: {annot_error}", exc_info=True)
                        # Continue processing even if annotation fails
                else:
                    logger.info(f"No bounding boxes found for {filename}, skipping annotation")

        # Add annotated file URLs to the result
        if annotated_files:
            result['annotated_files'] = annotated_files

        # Store in database
        try:
            session_id = db.create_session(
                application_type=f"custom:{schema_id}",
                summary=result.copy(),  # Make a copy since create_session modifies it
                files=file_data_list,
                user_id=user_id,
                api_key_id=api_key_id
            )
            result['session_id'] = session_id
            logger.info(f"Session created with ID: {session_id}")
        except Exception as db_error:
            logger.error(f"Failed to store session in database: {db_error}", exc_info=True)
            # Continue even if database storage fails

        return result
    except ExtractionError as e:
        logger.error(f"ExtractionError in extract_summary_custom: {str(e)}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in extract_summary_custom: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")



class FeedbackRequest(BaseModel):
    session_id: str
    field_name: str
    feedback_type: str  # "upvote" or "downvote"
    feedback_text: Optional[str] = None

@app.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    feedback_file = "data/feedback.csv"
    file_exists = os.path.isfile(feedback_file)
    
    try:
        with open(feedback_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "session_id", "field_name", "feedback_type", "feedback_text"])
            
            writer.writerow([
                datetime.now().isoformat(),
                feedback.session_id,
                feedback.field_name,
                feedback.feedback_type,
                feedback.feedback_text or ""
            ])
        return {"status": "success", "message": "Feedback recorded"}
    except Exception as e:
        logger.error(f"Error saving feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated")

if __name__ == "__main__":
    logger.info("Starting Document Validation Service on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)