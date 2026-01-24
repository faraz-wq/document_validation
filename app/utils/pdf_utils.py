"""Utility functions for PDF manipulation."""
import fitz  # PyMuPDF
from io import BytesIO
from typing import List, Dict, Any
from app.logging_config import get_logger

logger = get_logger(__name__)


def merge_pdfs(pdf_contents: List[bytes], filenames: List[str]) -> bytes:
    """
    Merge multiple PDF files into a single PDF.
    
    Args:
        pdf_contents: List of PDF file contents as bytes
        filenames: List of original filenames (for reference during debugging)
    
    Returns:
        Merged PDF content as bytes
    """
    logger.info(f"Merging {len(pdf_contents)} PDF files")
    
    if len(pdf_contents) == 0:
        raise ValueError("No PDF files provided")
    
    if len(pdf_contents) == 1:
        logger.info("Only one PDF provided, returning as-is")
        return pdf_contents[0]
    
    # Create a new PDF document to hold merged content
    merged_pdf = fitz.open()
    
    for i, (content, filename) in enumerate(zip(pdf_contents, filenames)):
        logger.info(f"Processing PDF {i+1}/{len(pdf_contents)}: {filename}")
        
        # Open the current PDF document
        current_doc = fitz.open(stream=content, filetype="pdf")
        
        # Copy all pages from current document to merged document
        for page_num in range(len(current_doc)):
            page = current_doc.load_page(page_num)
            merged_pdf.insert_pdf(current_doc, from_page=page_num, to_page=page_num)
        
        # Close the current document to free memory
        current_doc.close()
    
    # Save merged PDF to bytes
    merged_pdf_bytes = merged_pdf.write()
    merged_pdf.close()
    
    logger.info(f"Merged PDF created with {len(merged_pdf_bytes)} bytes")
    
    return merged_pdf_bytes


def is_pdf(content: bytes) -> bool:
    """
    Check if the given content is a PDF file by checking the header.
    
    Args:
        content: File content as bytes
    
    Returns:
        True if the content is a PDF, False otherwise
    """
    return content.startswith(b'%PDF-')


def combine_pdf_and_non_pdf_files(file_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Separate PDF and non-PDF files, combine PDFs into one, and return a list with the combined PDF
    and individual non-PDF files.
    
    Args:
        file_data_list: List of file data dictionaries containing 'filename', 'content', 'mime_type'
    
    Returns:
        List of file data dictionaries with PDFs combined into one
    """
    logger.info(f"Processing {len(file_data_list)} files for PDF combination")
    
    pdf_contents = []
    pdf_filenames = []
    non_pdf_files = []
    
    for file_data in file_data_list:
        content = file_data['content']
        filename = file_data['filename']
        
        if is_pdf(content):
            logger.info(f"Identified {filename} as PDF")
            pdf_contents.append(content)
            pdf_filenames.append(filename)
        else:
            logger.info(f"Identified {filename} as non-PDF ({file_data.get('mime_type', 'unknown')})")
            non_pdf_files.append(file_data)
    
    if len(pdf_contents) <= 1:
        logger.info(f"No need to combine PDFs - only {len(pdf_contents)} PDFs found")
        return file_data_list
    
    # Combine all PDFs into one
    logger.info(f"Combining {len(pdf_contents)} PDFs")
    combined_pdf_content = merge_pdfs(pdf_contents, pdf_filenames)
    
    # Create a new filename for the combined PDF
    combined_filename = f"combined_{'_'.join(pdf_filenames)}.pdf"
    
    # Create combined PDF file data
    combined_pdf_data = {
        "filename": combined_filename,
        "content": combined_pdf_content,
        "mime_type": "application/pdf"
    }
    
    # Return combined PDF plus non-PDF files
    result = [combined_pdf_data] + non_pdf_files
    logger.info(f"Result: {len(result)} files after combination ({len(pdf_contents)} PDFs combined into 1)")
    
    return result