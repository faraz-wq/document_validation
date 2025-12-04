"""
PDF Annotation Utility
Draws bounding boxes on PDF files based on extracted field locations.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Any
from app.logging_config import get_logger

logger = get_logger(__name__)


def draw_bounding_boxes_on_pdf(
    pdf_path: Path,
    bounding_boxes: Dict[str, Any],
    output_path: Path,
    color: tuple = (1, 0, 0),  # RGB normalized (red by default)
    opacity: float = 0.3,
    border_width: float = 2.0
) -> Path:
    """
    Draw bounding boxes on a PDF file.
    
    Args:
        pdf_path: Path to the input PDF file
        bounding_boxes: Dictionary mapping field names to BoundingBox objects
                       Each box has: filename, page, coordinates [y_min, x_min, y_max, x_max]
        output_path: Path where the annotated PDF will be saved
        color: RGB color tuple (normalized 0-1), default is red
        opacity: Opacity of the fill (0-1), default is 0.3
        border_width: Width of the border in points, default is 2.0
    
    Returns:
        Path to the annotated PDF file
    """
    logger.info(f"Annotating PDF: {pdf_path}")
    logger.debug(f"Number of bounding boxes to draw: {len(bounding_boxes)}")
    
    try:
        # Open the PDF
        doc = fitz.open(pdf_path)
        logger.debug(f"Opened PDF with {len(doc)} pages")
        
        # Group bounding boxes by page for efficient processing
        boxes_by_page = {}
        for field_name, box_data in bounding_boxes.items():
            # box_data is a dict with keys: filename, page, coordinates
            page_num = box_data.get('page', 1)  # 1-indexed
            if page_num not in boxes_by_page:
                boxes_by_page[page_num] = []
            boxes_by_page[page_num].append({
                'field_name': field_name,
                'coordinates': box_data.get('coordinates', [])
            })
        
        logger.debug(f"Bounding boxes grouped across {len(boxes_by_page)} pages")
        
        # Draw boxes on each page
        for page_num, boxes in boxes_by_page.items():
            # Convert to 0-indexed for fitz
            page_idx = page_num - 1
            
            if page_idx < 0 or page_idx >= len(doc):
                logger.warning(f"Page {page_num} is out of range for document with {len(doc)} pages")
                continue
            
            page = doc[page_idx]
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            logger.debug(f"Processing page {page_num}: {page_width}x{page_height} points")
            
            for box in boxes:
                coords = box['coordinates']
                field_name = box['field_name']
                
                if len(coords) != 4:
                    logger.warning(f"Invalid coordinates for field '{field_name}': {coords}")
                    continue
                
                # Coordinates are normalized to 1000x1000
                # Format: [y_min, x_min, y_max, x_max]
                y_min, x_min, y_max, x_max = coords
                
                # Convert from normalized (0-1000) to actual page coordinates
                # Note: PDF coordinate system has origin at bottom-left
                # But normalized coords from Gemini have origin at top-left
                x0 = (x_min / 1000.0) * page_width
                y0 = (y_min / 1000.0) * page_height
                x1 = (x_max / 1000.0) * page_width
                y1 = (y_max / 1000.0) * page_height
                
                # Create rectangle
                rect = fitz.Rect(x0, y0, x1, y1)
                
                # Draw rectangle with fill
                annot = page.add_rect_annot(rect)
                annot.set_colors(stroke=color, fill=color)
                annot.set_opacity(opacity)
                annot.set_border(width=border_width)
                annot.update()
                
                logger.debug(f"Drew box for field '{field_name}' on page {page_num}: {rect}")
        
        # Save the annotated PDF
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
        doc.close()
        
        logger.info(f"Successfully saved annotated PDF to: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error annotating PDF: {str(e)}", exc_info=True)
        raise


def annotate_document(
    file_path: Path,
    bounding_boxes: Dict[str, Any],
    output_dir: Path,
    filename_suffix: str = "_annotated"
) -> Path:
    """
    Annotate a document (PDF or image) with bounding boxes.
    For images, converts to PDF first.
    
    Args:
        file_path: Path to the input file
        bounding_boxes: Dictionary of bounding boxes
        output_dir: Directory where annotated file will be saved
        filename_suffix: Suffix to add to the output filename
    
    Returns:
        Path to the annotated file
    """
    logger.info(f"Annotating document: {file_path}")
    
    file_ext = file_path.suffix.lower()
    output_filename = f"{file_path.stem}{filename_suffix}.pdf"
    output_path = output_dir / output_filename
    
    # If it's already a PDF, annotate directly
    if file_ext == '.pdf':
        return draw_bounding_boxes_on_pdf(file_path, bounding_boxes, output_path)
    
    # If it's an image, convert to PDF first
    elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
        logger.info(f"Converting image to PDF: {file_path}")
        
        try:
            # Create a PDF from the image
            doc = fitz.open()
            img_doc = fitz.open(file_path)
            
            # Get image dimensions
            pdfbytes = img_doc.convert_to_pdf()
            img_pdf = fitz.open("pdf", pdfbytes)
            page = img_pdf[0]
            
            # Insert the page
            doc.insert_pdf(img_pdf)
            
            # Save temporary PDF
            temp_pdf = output_dir / f"{file_path.stem}_temp.pdf"
            doc.save(temp_pdf)
            doc.close()
            img_pdf.close()
            img_doc.close()
            
            # Now annotate the PDF
            result = draw_bounding_boxes_on_pdf(temp_pdf, bounding_boxes, output_path)
            
            # Clean up temporary file
            temp_pdf.unlink()
            
            return result
            
        except Exception as e:
            logger.error(f"Error converting image to PDF: {str(e)}", exc_info=True)
            raise
    
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")
