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

        ========================
        SOURCE DOCUMENTS
        ========================
        7. Populate "source_documents" with ALL files that contributed at least one extracted field.
        Each entry must include:
        - filename
        - inferred document type/title (e.g., "Aadhaar Card", "Income Certificate", "Application Form")
        - page_numbers: a list of page numbers (1-indexed) that correspond to this specific document type within the file.

        ========================
        CITATIONS (MANDATORY)
        ========================
        8. Populate the "citations" dictionary.
        9. EVERY extracted field (including nested fields and array elements) MUST have a citation.
        10. Use DOT NOTATION for field names, including array indices:
            Examples:
            - "applicant_name"
            - "income_details.total_gross_income"
            - "dependents[0].name"
        11. Citation value format:
            "Filename (Page X) - <Exact Text Snippet>"
            Provide the exact text snippet from the document that was used to extract the value.

        ========================
        FINAL VALIDATION
        ========================
        12. Ensure "citations" contain EXACTLY the same field keys as extracted data.
        13. Return the final JSON object ONLY.
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

        # 1. Perform OCR on all files
        ocr_results = [] # List of (filename, pages_output)
        parts = []
        
        system_prompt = self._create_prompt(app_type, schema_class)
        parts.append(system_prompt)

        for i, file_data in enumerate(files):
            filename = file_data['filename']
            content = file_data['content']
            mime_type = file_data.get('mime_type', 'application/pdf')
            
            # Basic mime type detection
            if not mime_type or mime_type == 'application/octet-stream':
                ext = filename.split('.')[-1].lower()
                if ext == 'pdf':
                    mime_type = 'application/pdf'
                elif ext in ['jpg', 'jpeg']:
                    mime_type = 'image/jpeg'
                elif ext == 'png':
                    mime_type = 'image/png'
                else:
                    mime_type = mime_type or 'application/octet-stream'

            logger.info(f"Performing OCR for file {i+1}: {filename}")
            try:
                pages_output = perform_ocr(content, mime_type)
                ocr_results.append((filename, pages_output))
                
                # Construct text representation for Gemini
                file_text = f"\n--- File: {filename} ---\n"
                for page in pages_output:
                    page_num = page['page']
                    page_text = "\n".join([block['text'] for block in page['blocks']])
                    file_text += f"Page {page_num}:\n{page_text}\n"
                
                parts.append(file_text)
                
            except Exception as e:
                logger.error(f"OCR failed for {filename}: {e}")
                raise ExtractionError(f"OCR failed for {filename}: {str(e)}")

        logger.info(f"Sending request to Gemini API with {len(parts)} parts")

        try:
            response = self.model.generate_content(
                parts,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.0,
                }
            )

            if response.candidates and response.candidates[0].finish_reason != FinishReason.STOP:
                logger.warning(f"Gemini API response did not finish with STOP reason. Finish reason: {response.candidates[0].finish_reason}")

            json_str = response.text
            
            # Clean up markdown
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]

            data = json.loads(json_str)
            logger.info(f"Successfully parsed JSON response with {len(data)} top-level keys")

            # Validate with Pydantic
            validated_data = schema_class(**data)
            result = validated_data.model_dump(by_alias=True)
            
            # 2. Resolve Bounding Boxes using OCR results
            logger.info("Resolving bounding boxes from OCR results")
            bounding_boxes = self._resolve_bounding_boxes(result, ocr_results)
            result['bounding_boxes'] = bounding_boxes
            
            # Extract token usage
            token_usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                token_usage = {
                    'prompt_token_count': response.usage_metadata.prompt_token_count,
                    'candidates_token_count': response.usage_metadata.candidates_token_count,
                    'total_token_count': response.usage_metadata.total_token_count,
                }
            result['_token_usage'] = token_usage
            
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Gemini: {str(e)}")
            raise ExtractionError(f"Failed to parse JSON response from Gemini: {str(e)}")
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
            
            # Skip very short values to avoid noise, unless it's likely a code or specific symbol
            if len(value_norm) < 2:
                pass

            for block in all_blocks:
                block_text_norm = block['text'].lower()
                
                # Check for substring match
                if value_norm in block_text_norm:
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

        traverse(data)
        return bounding_boxes

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