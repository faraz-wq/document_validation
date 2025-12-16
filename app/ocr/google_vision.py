import io
from typing import List, Dict, Any, Union
from google.cloud import vision
from pdf2image import convert_from_bytes
from app.logging_config import get_logger

logger = get_logger(__name__)

def perform_ocr(content: bytes, mime_type: str = "application/pdf") -> List[Dict[str, Any]]:
    """
    Performs OCR on the provided document content using Google Cloud Vision.
    
    Args:
        content: The file content in bytes.
        mime_type: The mime type of the file.
        
    Returns:
        A list of dictionaries, one per page, containing page metadata and text blocks.
    """
    client = vision.ImageAnnotatorClient()
    pages_output = []

    images = []
    if mime_type == "application/pdf":
        try:
            # Convert PDF to images (300 DPI)
            images = convert_from_bytes(content, dpi=300)
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            raise
    elif mime_type.startswith("image/"):
        # For images, we just have one "page"
        from PIL import Image
        image = Image.open(io.BytesIO(content))
        images = [image]
    else:
        raise ValueError(f"Unsupported mime type for OCR: {mime_type}")

    for page_num, image in enumerate(images, start=1):
        width, height = image.size
        
        # Convert PIL image to bytes for Vision API
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="PNG")
        content_bytes = img_byte_arr.getvalue()
        
        vision_image = vision.Image(content=content_bytes)
        
        # Perform text detection
        response = client.document_text_detection(image=vision_image)
        
        if response.error.message:
            raise Exception(f"Vision API Error: {response.error.message}")
            
        blocks = []
        # Iterate through pages -> blocks -> paragraphs -> words -> symbols if needed
        # The requirement says "Extract word-level or paragraph-level text with pixel bounding boxes"
        # Let's go with paragraph level for blocks, or maybe symbols for higher precision?
        # Usually blocks or paragraphs are good enough for field matching.
        # Let's use the full text annotation structure.
        
        full_text_annotation = response.full_text_annotation
        
        if full_text_annotation:
            for page in full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        # Reconstruct paragraph text
                        para_text = ""
                        for word in paragraph.words:
                            word_text = "".join([symbol.text for symbol in word.symbols])
                            para_text += word_text + " "
                        
                        para_text = para_text.strip()
                        
                        if not para_text:
                            continue

                        # Get bounding box for the paragraph
                        # Vertices are in order: top-left, top-right, bottom-right, bottom-left
                        vertices = paragraph.bounding_box.vertices
                        
                        x_coords = [v.x for v in vertices]
                        y_coords = [v.y for v in vertices]
                        
                        x_min = min(x_coords)
                        x_max = max(x_coords)
                        y_min = min(y_coords)
                        y_max = max(y_coords)
                        
                        blocks.append({
                            "text": para_text,
                            "bbox_px": [y_min, x_min, y_max, x_max]
                        })

        pages_output.append({
            "page": page_num,
            "image_width": width,
            "image_height": height,
            "blocks": blocks
        })
        
        logger.info(f"Page {page_num}: Found {len(blocks)} text blocks")
        # Log full text for observability
        page_full_text = "\n".join([b['text'] for b in blocks])
        logger.debug(f"Page {page_num} Content:\n{page_full_text}")
        
    return pages_output
