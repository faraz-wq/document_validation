"""
FastAPI Application for Document Validation Workflow
Takes file inputs, processes through two-stage workflow, and displays results in HTML
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import markdown
from fastapi import FastAPI, UploadFile, Form, HTTPException, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from fastapi import Request

# Add src directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import DocumentValidationWorkflow
from src.certificate_types import CertificateType, CertificateSpecs

# Get the directory of this file to construct absolute paths
current_dir = Path(__file__).parent

app = FastAPI(title="Document Validation API", description="API for document validation workflow")
templates = Jinja2Templates(directory=str(current_dir / "templates"))

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(current_dir / "static")), name="static")

class FileValidationError(Exception):
    """Custom exception for file validation errors"""
    pass

def validate_uploaded_files(files: List[UploadFile]) -> List[Path]:
    """Validate uploaded files and return their paths"""
    # Create temporary directory to store uploaded files
    temp_dir = Path(tempfile.mkdtemp())
    file_paths = []
    
    for file in files:
        # Check if file is provided
        if not file or not file.filename:
            raise FileValidationError("File is required")
        
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
            raise FileValidationError(f"Unsupported file format: {file_ext}. Supported formats: .pdf, .jpg, .jpeg, .png")
        
        # Check file size (max 20MB)
        file.file.seek(0, 2)  # Seek to end of file
        file_size = file.file.tell()
        file.file.seek(0)  # Reset file pointer to beginning
        if file_size > 20 * 1024 * 1024:  # 20MB in bytes
            raise FileValidationError(f"File size too large: {file_size} bytes. Maximum allowed: 20MB")
        
        # Save file temporarily
        temp_file_path = temp_dir / file.filename
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_paths.append(temp_file_path)
    
    return file_paths

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Render the main upload page"""
    certificate_types = CertificateSpecs.get_certificate_types()
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "certificate_types": certificate_types,
        "title": "Document Validation System"
    })

@app.post("/process", response_class=HTMLResponse)
async def process_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    cert_type: str = Form(...),
    document_names: str = Form(default="")
):
    """Process uploaded documents through the two-stage workflow"""
    try:
        # Validate inputs
        if not files or all(not f.filename for f in files):
            raise HTTPException(status_code=400, detail="At least one file is required")
        
        if not cert_type:
            raise HTTPException(status_code=400, detail="Certificate type is required")
        
        # Validate certificate type
        try:
            cert_enum = CertificateSpecs.from_string(cert_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid certificate type: {cert_type}")
        
        # Validate and save uploaded files
        file_paths = validate_uploaded_files(files)
        
        # Parse document names if provided
        document_names_list = None
        if document_names.strip():
            document_names_list = [name.strip() for name in document_names.split(",") if name.strip()]
            # Ensure number of names matches number of files
            if len(document_names_list) != len(file_paths):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Number of document names ({len(document_names_list)}) must match number of files ({len(file_paths)})"
                )
        
        # Create workflow and run complete processing
        workflow = DocumentValidationWorkflow()
        result = workflow.run_complete_workflow(
            file_paths=file_paths,
            cert_type=cert_enum,
            document_names=document_names_list,
            save_intermediate=True
        )
        
        # Convert markdown summary to HTML
        stage2_html = ""
        if result["stage2_result"] and result["stage2_result"].success:
            stage2_html = markdown.markdown(result["stage2_result"].summary_table, extensions=['tables'])
        
        # Prepare Stage 1 results data
        stage1_results_data = []
        for extraction_result in result["stage1_results"]:
            stage1_data = {
                "document_id": extraction_result.document_id,
                "file_name": extraction_result.file_name,
                "success": extraction_result.success,
                "error_message": extraction_result.error_message,
                "extracted_text": extraction_result.extracted_text if extraction_result.success else "No extraction available"
            }
            stage1_results_data.append(stage1_data)
        
        # Render results page
        return templates.TemplateResponse("results.html", {
            "request": request,
            "workflow_result": result,
            "stage1_results": stage1_results_data,
            "stage2_html": stage2_html,
            "title": f"Processing Results - {cert_type.title()} Certificate"
        })
        
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error processing documents: {str(e)}")
        print(error_trace)
        
        raise HTTPException(status_code=500, detail=f"Error processing documents: {str(e)}")
    finally:
        # Clean up temporary files
        if 'file_paths' in locals():
            for file_path in file_paths:
                if file_path.exists():
                    file_path.unlink()
            temp_dir = file_path.parent
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/process", response_class=JSONResponse)
async def process_documents_api(
    files: List[UploadFile] = File(...),
    cert_type: str = Form(...),
    document_names: str = Form(default="")
):
    """API endpoint for processing documents - returns JSON response"""
    try:
        # Validate inputs
        if not files or all(not f.filename for f in files):
            raise HTTPException(status_code=400, detail="At least one file is required")
        
        if not cert_type:
            raise HTTPException(status_code=400, detail="Certificate type is required")
        
        # Validate certificate type
        try:
            cert_enum = CertificateSpecs.from_string(cert_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid certificate type: {cert_type}")
        
        # Validate and save uploaded files
        file_paths = validate_uploaded_files(files)
        
        # Parse document names if provided
        document_names_list = None
        if document_names.strip():
            document_names_list = [name.strip() for name in document_names.split(",") if name.strip()]
            # Ensure number of names matches number of files
            if len(document_names_list) != len(file_paths):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Number of document names ({len(document_names_list)}) must match number of files ({len(file_paths)})"
                )
        
        # Create workflow and run complete processing
        workflow = DocumentValidationWorkflow()
        result = workflow.run_complete_workflow(
            file_paths=file_paths,
            cert_type=cert_enum,
            document_names=document_names_list,
            save_intermediate=True
        )
        
        # Return JSON response
        return JSONResponse(content=result)
        
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the error
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error processing documents: {str(e)}")
        print(error_trace)
        
        raise HTTPException(status_code=500, detail=f"Error processing documents: {str(e)}")
    finally:
        # Clean up temporary files
        if 'file_paths' in locals():
            for file_path in file_paths:
                if file_path.exists():
                    file_path.unlink()
            temp_dir = file_path.parent
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)