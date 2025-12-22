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

    import concurrent.futures

    def process_page(page_args):
        page_num, image = page_args
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
        full_text_annotation = response.full_text_annotation
        
        if full_text_annotation:
            for page in full_text_annotation.pages:
                for block in page.blocks:
                    for paragraph in block.paragraphs:
                        para_text = ""
                        for word in paragraph.words:
                            word_text = "".join([symbol.text for symbol in word.symbols])
                            para_text += word_text + " "
                        
                        para_text = para_text.strip()
                        if not para_text:
                            continue

                        vertices = paragraph.bounding_box.vertices
                        x_coords = [v.x for v in vertices if hasattr(v, 'x')]
                        y_coords = [v.y for v in vertices if hasattr(v, 'y')]
                        
                        if not x_coords or not y_coords:
                            continue
                            
                        x_min, x_max = min(x_coords), max(x_coords)
                        y_min, y_max = min(y_coords), max(y_coords)
                        
                        blocks.append({
                            "text": para_text,
                            "bbox_px": [y_min, x_min, y_max, x_max],
                            "words": [
                                {
                                    "text": "".join([s.text for s in w.symbols]),
                                    "bbox_px": [
                                        min([v.y for v in w.bounding_box.vertices if hasattr(v, 'y')]),
                                        min([v.x for v in w.bounding_box.vertices if hasattr(v, 'x')]),
                                        max([v.y for v in w.bounding_box.vertices if hasattr(v, 'y')]),
                                        max([v.x for v in w.bounding_box.vertices if hasattr(v, 'x')])
                                    ]
                                } for w in paragraph.words
                            ]
                        })

        return {
            "page": page_num,
            "image_width": width,
            "image_height": height,
            "blocks": blocks,
            "image_bytes": content_bytes
        }

    # Process pages in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(images), 10)) as executor:
        future_to_page = {executor.submit(process_page, (i, img)): i for i, img in enumerate(images, start=1)}
        
        results = []
        for future in concurrent.futures.as_completed(future_to_page):
            results.append(future.result())
            
    # Sort by page number to maintain order
    pages_output = sorted(results, key=lambda x: x['page'])
    
    for page in pages_output:
        logger.info(f"Page {page['page']}: Found {len(page['blocks'])} text blocks")
        
    return pages_output
