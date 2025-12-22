import os
import base64
import json
from typing import List, Dict, Type, Any, Optional, Tuple
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
from pydantic import BaseModel
import app.models as schemas
from app.logging_config import get_logger
from app.core.schema_registry import schema_registry
from app.core.dynamic_model_generator import DynamicModelGenerator
from app.ocr.google_vision import perform_ocr

logger = get_logger(__name__)

# Initialize Vertex AI
# Ensure GOOGLE_APPLICATION_CREDENTIALS is set in the environment or .env
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if project_id:
    vertexai.init(project=project_id, location=location)

class ExtractionError(Exception):
    """Custom exception for extraction failures."""
    pass

class ConfigurableExtractor:
    def __init__(self, model_name: str = "gemini-2.5-flash", user_id: str = "default"):
        self.model = GenerativeModel(model_name)
        self.user_id = user_id
        logger.info(f"ConfigurableExtractor initialized with model: {model_name} for user: {user_id}")

    def _get_schema_for_type(self, app_type: str) -> Type[BaseModel]:
        """Maps application type to the corresponding Pydantic model (handles both default and custom schemas)."""
        logger.debug(f"Mapping application type: {app_type} to schema")
        
        # Check if this is a custom schema request
        if app_type.startswith("custom:"):
            schema_id = app_type.replace("custom:", "")
            schema_def = schema_registry.get_schema(schema_id, self.user_id)
            if not schema_def:
                logger.error(f"Custom schema not found or access denied: {schema_id}")
                raise ValueError(f"Custom schema not found or access denied: {schema_id}")
            
            # Generate dynamic model from schema definition
            dynamic_model = DynamicModelGenerator.create_model_from_schema(
                schema_def.fields, 
                schema_def.schema_id
            )
            logger.debug(f"Generated dynamic model for custom schema: {schema_def.schema_id}")
            return dynamic_model

        # Handle default application types (original logic)
        mapping = {
            "Integrated Certificate": schemas.IntegratedCertificateSummary,
            "Income Certificate": schemas.IncomeCertificateSummary,
            "OBC Certificate": schemas.OBCCertificateSummary,
            "EWS Certificate": schemas.EWSCertificateSummary,
            "Family Member Certificate": schemas.FamilyMemberCertificateSummary,
        }
        if app_type not in mapping:
            logger.error(f"Unknown application type: {app_type}")
            raise ValueError(f"Unknown application type: {app_type}")

        schema_class = mapping[app_type]
        logger.debug(f"Mapped {app_type} to schema: {schema_class.__name__}")
        return schema_class

    def _create_prompt(self, app_type: str, schema_class: Type[BaseModel]) -> str:
        """Constructs the system prompt with schema instructions."""
        logger.debug(f"Creating prompt for application type: {app_type} with schema: {schema_class.__name__}")
        schema_json = schema_class.model_json_schema()

        prompt = f"""
        You are an expert document analysis AI. Your task is to extract structured information from the provided documents for a "{app_type}" application.

        STRICTLY follow this JSON schema for the output:
        {json.dumps(schema_json, indent=2)}

        ========================
        CRITICAL OUTPUT RULES
        ========================
        - Return ONLY a single valid JSON object.
        - Do NOT include markdown, explanations, comments, or extra text.
        - The JSON MUST strictly conform to the provided schema.
        - Do NOT invent fields that are not present in the schema.
        - LEAVE "bounding_boxes" EMPTY. You should NOT generate coordinates.

        ========================
        DOCUMENT ANALYSIS RULES
        ========================
        1. Analyze ALL provided document text.
        2. Treat all documents as potentially relevant unless clearly unrelated.
        3. Do NOT assume values from prior knowledge — only use visible document content.

        ========================
        FIELD EXTRACTION RULES
        ========================
        4. Extract ONLY the fields defined in the schema.
        5. For each field:
        - If found: extract exactly as written in the document (no rephrasing).
        - If optional and not found: use null.
        - If required and not found:
            - Infer ONLY if the inference is extremely safe and unambiguous.
            - Otherwise set null and add an entry to a top-level "_errors" array explaining the missing field.
        6. For array fields:
        - Return an empty list [] if no items are found.
        - Each array element must be fully populated according to the schema.
        7. For person names:
        - EXCLUDE honorifics, titles, and prefixes such as "Late", "Mr.", "Mrs.", "Ms.", "Dr.", etc. Extract only the actual name.
        - For example: if the document says "Late Rajesh Kumar", extract "Rajesh Kumar".

        ========================
        SOURCE DOCUMENTS (PAGE CLASSIFICATION)
        ========================
        8. Classify EVERY page of the provided files.
        9. Populate "source_documents" to show which document type each page belongs to.
        10. EVERY page number (1-indexed) across all files MUST be accounted for in this list, even if no fields were extracted from that page.
        11. Each entry must include:
        - filename
        - inferred document type/title (e.g., "Aadhaar Card", "Salary Slip", "Application Form")
        - page_numbers: a list of page numbers that correspond to this specific document type within that file.

        ========================
        CITATIONS (MANDATORY)
        ========================
        12. Populate the "citations" dictionary.
        13. EVERY extracted field (including nested fields and array elements) MUST have a citation.
        14. IMPORTANT: For key verification fields (Applicant Name, DOB, Income amounts), cite ALL occurrences across ALL supporting documents (e.g. cite both the Application and the Aadhaar Card) as a list of strings.
        15. Use DOT NOTATION for field names, including array indices:
            Examples:
            - "applicant_name"
            - "income_details.total_gross_income"
            - "dependents[0].name"
        16. Citation value format:
            "Filename (Page X) - <Exact Text Snippet>"
            Provide the exact text snippet from the document that was used to extract the value.

        ========================
        MULTIMODAL REASONING & REMARKS
        ========================
        16. Use BOTH the OCR text AND the provide page images for extraction.
        17. Look for visual cues (stamps, signatures, photos, handwriting) in the images that OCR might miss.
        18. Populate "field_remarks" (Dict[str, str]) with specific notes for any field where you notice discrepancies or interesting visual patterns (e.g., {{"applicant_name": "Name spelled differently on Aadhar page 3"}}).
        19. Use DOT NOTATION for keys in "field_remarks".

        """

        logger.debug(f"Prompt created with length: {len(prompt)} characters")
        return prompt

    def extract(self, app_type: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts data using Gemini with OCR-based bounding boxes.

        Args:
            app_type: The type of application (e.g., "Income Certificate" or "custom:schema_id").
            files: A list of dicts, each containing 'filename' (str) and 'content' (bytes).

        Returns:
            A dictionary matching the schema.
        """
        logger.info(f"Starting extraction for application type: {app_type} with {len(files)} files")

        try:
            schema_class = self._get_schema_for_type(app_type)
            logger.debug(f"Schema class determined: {schema_class.__name__}")
        except ValueError as e:
            logger.error(f"Failed to get schema for application type {app_type}: {str(e)}")
            raise ExtractionError(str(e))

        import concurrent.futures

        # 1. Perform OCR on all files in parallel
        ocr_results = []
        parts = [self._create_prompt(app_type, schema_class)]

        def ocr_task(file_data):
            filename = file_data['filename']
            content = file_data['content']
            mime_type = file_data.get('mime_type')
            
            if not mime_type or mime_type == 'application/octet-stream':
                ext = filename.split('.')[-1].lower()
                mime_type = {
                    'pdf': 'application/pdf',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png'
                }.get(ext, 'application/octet-stream')

            logger.info(f"Performing OCR for: {filename}")
            try:
                pages_output = perform_ocr(content, mime_type)
                return filename, pages_output
            except Exception as e:
                logger.error(f"OCR failed for {filename}: {e}")
                raise ExtractionError(f"OCR failed for {filename}: {str(e)}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(files)) as executor:
            task_results = list(executor.map(ocr_task, files))

        for filename, pages_output in task_results:
            ocr_results.append((filename, pages_output))
            
            parts.append(f"\n--- File: {filename} ---\n")
            for page in pages_output:
                page_num = page['page']
                page_text = "\n".join([block['text'] for block in page['blocks']])
                
                parts.append(f"Page {page_num} OCR Text:\n{page_text}")
                
                # Add image part for multimodal reasoning
                parts.append(Part.from_data(
                    data=page['image_bytes'],
                    mime_type="image/png"
                ))
        
        logger.info(f"Sending multimodal request to Gemini API with {len(parts)} parts")
        try:
            response = self.model.generate_content(
                parts,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.0,
                }
            )

            json_str = response.text
            if json_str.startswith("```json"): json_str = json_str[7:]
            if json_str.endswith("```"): json_str = json_str[:-3]

            data = json.loads(json_str)
            
            # Validate with Pydantic
            validated_data = schema_class(**data)
            result = validated_data.model_dump(by_alias=True)
            
            # 2. Resolve Bounding Boxes
            logger.info("Resolving bounding boxes from OCR results")
            result['bounding_boxes'] = self._resolve_bounding_boxes(result, ocr_results)
            
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                result['_token_usage'] = {
                    'prompt_token_count': response.usage_metadata.prompt_token_count,
                    'candidates_token_count': response.usage_metadata.candidates_token_count,
                    'total_token_count': response.usage_metadata.total_token_count,
                }
            
            return result
        except Exception as e:
            logger.error(f"Gemini extraction failed: {str(e)}", exc_info=True)
            raise ExtractionError(f"Gemini extraction failed: {str(e)}")

    def _resolve_bounding_boxes(self, data: Dict[str, Any], ocr_results: List[Tuple[str, List[Dict[str, Any]]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Resolves bounding boxes by matching extracted values to OCR blocks.
        """
        bounding_boxes = {}
        
        # Flatten OCR blocks for easier searching
        # List of (text, bbox_px, page, filename, width, height)
        all_blocks = []
        for filename, pages in ocr_results:
            for page in pages:
                width = page['image_width']
                height = page['image_height']
                page_num = page['page']
                for block in page['blocks']:
                    all_blocks.append({
                        'text': block['text'],
                        'bbox_px': block['bbox_px'],
                        'words': block.get('words', []),
                        'page': page_num,
                        'filename': filename,
                        'width': width,
                        'height': height
                    })
        
        logger.info(f"Total OCR blocks available for matching: {len(all_blocks)}")

        def find_matching_blocks(value: str) -> List[Dict[str, Any]]:
            if not value or not isinstance(value, str):
                return []
            
            matches = []
            value_norm = value.lower().strip()
            
            # Skip very short values to avoid noise
            if len(value_norm) < 2:
                return []

            # PASS 1: Direct Substring Match (Case-Insensitive)
            for block in all_blocks:
                block_text_norm = block['text'].lower()
                if value_norm in block_text_norm:
                    words = block.get('words', [])
                    if words:
                        start_pos = 0
                        while True:
                            idx = block_text_norm.find(value_norm, start_pos)
                            if idx == -1: break
                            
                            end_idx = idx + len(value_norm)
                            current_offset = 0
                            matching_coords = []
                            for w in words:
                                w_len = len(w['text'])
                                w_start = current_offset
                                w_end = current_offset + w_len
                                if not (w_end <= idx or w_start >= end_idx):
                                    matching_coords.append(w['bbox_px'])
                                current_offset += w_len + 1 # space
                            
                            if matching_coords:
                                y_min = min(c[0] for c in matching_coords)
                                x_min = min(c[1] for c in matching_coords)
                                y_max = max(c[2] for c in matching_coords)
                                x_max = max(c[3] for c in matching_coords)
                                match_occurrence = block.copy()
                                match_occurrence['bbox_px'] = [y_min, x_min, y_max, x_max]
                                matches.append(match_occurrence)
                            else:
                                if block not in matches: matches.append(block)
                            start_pos = idx + 1
                    else:
                        matches.append(block)
            
            # PASS 2: Fragmented Matching (for compound fields like addresses)
            if not matches and len(value_norm) > 15:
                # Split by commas or major delimiters
                fragments = [f.strip() for f in value.split(',') if len(f.strip()) > 5]
                if not fragments: # fallback to word chunks
                    words_list = value.split()
                    fragments = [" ".join(words_list[i:i+3]) for i in range(0, len(words_list), 3) if len(" ".join(words_list[i:i+3])) > 5]

                for fragment in fragments:
                    frag_norm = fragment.lower()
                    for block in all_blocks:
                        if frag_norm in block['text'].lower():
                            if block not in matches:
                                matches.append(block)
            
            return matches

        def traverse(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ['bounding_boxes', 'citations', 'source_documents', '_errors', '_token_usage']:
                        continue
                    new_path = f"{path}.{k}" if path else k
                    traverse(v, new_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_path = f"{path}[{i}]"
                    traverse(item, new_path)
            elif isinstance(obj, (str, int, float)) and obj is not None:
                val_str = str(obj)
                # Find ALL matching blocks
                matches = find_matching_blocks(val_str)
                
                if matches:
                    logger.info(f"Field '{path}': Found {len(matches)} matches for value '{val_str}'")
                    
                    if path not in bounding_boxes:
                        bounding_boxes[path] = []
                        
                    for match in matches:
                        # Calculate normalized coordinates scaled to 1000
                        y_min, x_min, y_max, x_max = match['bbox_px']
                        width = match['width']
                        height = match['height']
                        
                        # Normalize 0-1 then scale to 1000
                        norm_box = [
                            (y_min / height) * 1000,
                            (x_min / width) * 1000,
                            (y_max / height) * 1000,
                            (x_max / width) * 1000
                        ]
                        
                        # Find document title for this page
                        doc_title = None
                        if 'source_documents' in data and isinstance(data['source_documents'], list):
                            for doc in data['source_documents']:
                                # Check if this doc matches filename and contains the page
                                if isinstance(doc, dict):
                                    doc_filename = doc.get('filename')
                                    doc_pages = doc.get('page_numbers', [])
                                    if doc_filename == match['filename'] and match['page'] in doc_pages:
                                        doc_title = doc.get('document_title')
                                        break
                        
                        box_entry = {
                            "filename": match['filename'],
                            "document_title": doc_title, 
                            "page": match['page'],
                            "coordinates": norm_box
                        }
                        bounding_boxes[path].append(box_entry)
                else:
                    logger.warning(f"Field '{path}': No OCR match found for value '{val_str}'")

    def generate_validation_summary(self, result: Dict[str, Any]) -> str:
        """
        Generates a very short natural language summary of missing and mismatched fields.
        """
        logger.info("Generating validation summary")
        errors = result.get('_errors', [])
        
        # Find fields that are null or empty in the extraction summary
        missing_fields = []
        def find_missing(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in ['bounding_boxes', 'citations', 'source_documents', '_errors', '_token_usage']:
                        continue
                    new_path = f"{path}.{k}" if path else k
                    find_missing(v, new_path)
            elif obj is None or obj == "" or (isinstance(obj, list) and len(obj) == 0):
                missing_fields.append(path)
        
        find_missing(result)
        
        if result.get('validation_summary'):
            return result['validation_summary']

        if not errors and not missing_fields:
            return None

        prompt = f"""
        Provide a VERY SHORT (one sentence) summary of these issues:
        Errors: {json.dumps(errors)}
        Missing: {", ".join(missing_fields)}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,
                    "max_output_tokens": 150,
                }
            )
            summary = response.text.strip()
            logger.info(f"Generated validation summary: {summary}")
            return summary
        except Exception as e:
            logger.error(f"Failed to generate validation summary: {e}")
            return "Discrepancies found in extraction. Please review the flagged fields."

# Helper to load file content (for testing/CLI)
def load_file(filepath: str) -> Dict[str, Any]:
    logger.debug(f"Loading file content from: {filepath}")
    with open(filepath, "rb") as f:
        content = f.read()

    result = {
        "filename": os.path.basename(filepath),
        "content": content,
        "mime_type": None # Let extractor detect
    }

    logger.info(f"Successfully loaded file: {result['filename']}, size: {len(content)} bytes")
    return result