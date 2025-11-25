"""
PDF Processor - Handles multi-page PDF processing
Extracts pages individually for more comprehensive field detection
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from PIL import Image
from io import BytesIO

try:
    import PyPDF2
    from PyPDF2 import PdfReader
except ImportError:
    raise ImportError("PyPDF2 is required for PDF processing. Please install it with 'pip install PyPDF2'")

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handle PDF processing with page-by-page extraction capability"""
    
    def __init__(self):
        logger.info("PDFProcessor initialized")
    
    def split_pdf_to_pages(self, pdf_path: Path, output_dir: Optional[Path] = None) -> List[Path]:
        """
        Split a PDF into individual page PDFs

        Args:
            pdf_path: Path to the input PDF file
            output_dir: Directory to save individual pages (uses temp dir if not provided)

        Returns:
            List of paths to individual page PDFs
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="pdf_pages_"))
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Splitting PDF '{pdf_path.name}' into individual pages")
        
        page_files = []
        try:
            with open(pdf_path, 'rb') as pdf_file:
                reader = PdfReader(pdf_file)
                total_pages = len(reader.pages)
                logger.info(f"PDF has {total_pages} pages")
                
                for page_num in range(total_pages):
                    # Create a new PDF writer for this page
                    from PyPDF2 import PdfWriter
                    
                    writer = PdfWriter()
                    writer.add_page(reader.pages[page_num])
                    
                    # Create output file path
                    page_filename = f"{pdf_path.stem}_page_{page_num + 1}.pdf"
                    page_path = output_dir / page_filename
                    
                    # Write the page to a new PDF file
                    with open(page_path, 'wb') as output_pdf:
                        writer.write(output_pdf)
                    
                    page_files.append(page_path)
                    logger.debug(f"Saved page {page_num + 1} as {page_path.name}")
        
        except Exception as e:
            logger.error(f"Error splitting PDF: {str(e)}")
            raise
        
        logger.info(f"Created {len(page_files)} individual page files")
        return page_files
    
    def extract_text_from_pdf(self, pdf_path: Path) -> List[str]:
        """
        Extract text from each page of a PDF

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of text content for each page
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        page_texts = []
        try:
            with open(pdf_path, 'rb') as pdf_file:
                reader = PdfReader(pdf_file)
                total_pages = len(reader.pages)
                
                for page_num in range(total_pages):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    page_texts.append(page_text)
                    
                    logger.debug(f"Extracted text from page {page_num + 1} "
                                f"({len(page_text)} characters)")
        
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
        
        return page_texts
    
    def pdf_to_images(self, pdf_path: Path, dpi: int = 200) -> List[Image.Image]:
        """
        Convert PDF pages to images using pdf2image if available
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for image conversion
            
        Returns:
            List of PIL Image objects for each page
        """
        try:
            # Try to import pdf2image
            from pdf2image import convert_from_path
        except ImportError:
            logger.warning("pdf2image not available. Install with 'pip install pdf2image[all]'")
            logger.warning("Falling back to PyPDF2 text extraction only")
            # Return empty list to indicate we can't convert to images
            return []
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Convert PDF to list of images
            images = convert_from_path(pdf_path, dpi=dpi)
            logger.info(f"Converted {len(images)} pages to images from {pdf_path.name}")
            return images
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise
    
    def save_images_as_pdfs(self, images: List[Image.Image], output_dir: Path) -> List[Path]:
        """
        Save PIL images as individual PDF files
        
        Args:
            images: List of PIL Image objects
            output_dir: Directory to save the PDF files
            
        Returns:
            List of paths to saved PDF files
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_files = []
        
        for idx, image in enumerate(images):
            # Create a BytesIO buffer to save the image as PDF
            img_buffer = BytesIO()
            image.save(img_buffer, format='PDF', resolution=100.0)
            img_buffer.seek(0)
            
            # Save to file
            pdf_path = output_dir / f"page_{idx + 1}.pdf"
            with open(pdf_path, 'wb') as f:
                f.write(img_buffer.getvalue())
            
            saved_files.append(pdf_path)
        
        logger.info(f"Saved {len(saved_files)} PDF pages from images")
        return saved_files

    def extract_fields_from_pages(
        self, 
        page_files: List[Path], 
        page_texts: List[str]
    ) -> Dict[str, Any]:
        """
        Extract all possible fields from each page and combine results
        
        Args:
            page_files: List of individual page PDF files
            page_texts: List of text extracted from each page
            
        Returns:
            Dictionary with combined field extractions from all pages
        """
        combined_fields = {}
        
        for idx, (page_file, page_text) in enumerate(zip(page_files, page_texts)):
            logger.info(f"Processing page {idx + 1}: {page_file.name}")
            
            # Extract fields from page text
            page_fields = self._extract_fields_from_text(page_text, page_idx=idx+1)
            combined_fields.update(page_fields)
        
        logger.info(f"Extracted fields from {len(page_files)} pages")
        return combined_fields

    def _extract_fields_from_text(self, text: str, page_idx: int) -> Dict[str, str]:
        """
        Extract potential fields from text content
        
        Args:
            text: Text content to extract fields from
            page_idx: Current page index for reference
            
        Returns:
            Dictionary of field names and values
        """
        fields = {}
        
        # Basic patterns to extract common fields
        import re
        
        # Name patterns
        name_patterns = [
            r'(?:Name|NAME|name)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:Applicant Name|Applicant|Applicant\'?s Name|FullName)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        # Date patterns
        date_patterns = [
            r'(?:DOB|Date of Birth|Birth Date|Date Of Birth)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})',
            r'(?:Date|DATE|date)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4}|\d{4}[\/\-]\d{2}[\/\-]\d{2})',
        ]
        
        # Address patterns
        address_patterns = [
            r'(?:Address|ADDRESS|address)\s*[:\-]?\s*([A-Za-z0-9\s,.\-#]+?)(?:\n|$)',
        ]
        
        # Find all matches
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                fields[f"Page_{page_idx}_Name"] = matches[0].strip()
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                fields[f"Page_{page_idx}_Date"] = matches[0].strip()
        
        for pattern in address_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                fields[f"Page_{page_idx}_Address"] = matches[0].strip()
        
        # Also add any other potential fields with their positions
        # This is a simple approach - in real implementation, use more sophisticated NLP
        other_patterns = [
            r'(?:Father\'?s Name|Father Name|Father)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:Mother\'?s Name|Mother Name|Mother)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'(?:Phone|Phone Number|Mobile|Mobile Number)\s*[:\-]?\s*(\d{10}|\d{5}[-\s]?\d{5})',
            r'(?:Email|E-mail|Email ID)\s*[:\-]?\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
            r'(?:Income|Annual Income|Total Income)\s*[:\-]?\s*([₹$€£\d,.\s]+)',
        ]
        
        for pattern in other_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for i, match in enumerate(matches):
                if isinstance(match, tuple):
                    match = match[0]  # Get the first captured group
                field_name = f"Page_{page_idx}_Field_{len(fields) + 1}"
                fields[field_name] = match.strip()
        
        return fields