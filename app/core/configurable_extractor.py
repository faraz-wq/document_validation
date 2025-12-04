import os
import base64
import json
from typing import List, Dict, Type, Any, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
from pydantic import BaseModel
import app.models as schemas
from app.logging_config import get_logger
from app.core.schema_registry import schema_registry
from app.core.dynamic_model_generator import DynamicModelGenerator

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
    def __init__(self, model_name: str = "gemini-2.5-pro", user_id: str = "default"):
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
        You are an expert document analysis AI. Your task is to extract structured information from the provided documents.

        STRICTLY follow this JSON schema for the output:
        {json.dumps(schema_json, indent=2)}

        Instructions:
        1. Analyze ALL provided document images/PDFs.
        2. Extract the fields defined in the schema.
        3. If a field is not found in the documents, use null (None) if it is optional. If it is required but missing, try to infer it from context if safe, otherwise fail or return a clear error indicator (but prefer returning the JSON with nulls where allowed).
        4. Populate 'source_documents' with the filename and inferred document title (e.g., 'Aadhaar Card', 'Application Form') for each file you processed that contributed data.
        5. Populate the 'citations' dictionary. For EVERY extracted field (including nested ones), add an entry where the key is the field name (using dot notation, e.g., 'applicant_name', 'income_details.total_gross_income') and the value is the source string containing the "Filename (Page X)". Example: "applicant_name": "application_form.pdf (Page 1)".
        6. Populate the 'bounding_boxes' dictionary. For EVERY extracted field, provide the bounding box coordinates where that data appears in the document. Use the field name as the key (with dot notation for nested fields) and provide an object with:
           - "filename": the source filename
           - "page": the page number (1-indexed)
           - "coordinates": an array of 4 numbers [y_min, x_min, y_max, x_max] representing the normalized bounding box scaled to 1000x1000, where (0,0) is the top-left corner
        7. Return ONLY the valid JSON object. Do not include markdown formatting like ```json ... ```.
        """

        logger.debug(f"Prompt created with length: {len(prompt)} characters")
        return prompt

    def extract(self, app_type: str, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts data using Gemini.

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

        system_prompt = self._create_prompt(app_type, schema_class)
        logger.debug("System prompt created successfully")

        parts = [system_prompt]
        logger.info("Processing file data for Gemini API")

        for i, file_data in enumerate(files):
            filename = file_data['filename']
            content = file_data['content']
            mime_type = file_data.get('mime_type', 'application/pdf') # Default to PDF if not specified

            logger.debug(f"Processing file {i+1}: {filename}, size: {len(content)} bytes")

            # Basic mime type detection if not provided or generic
            if not mime_type or mime_type == 'application/octet-stream':
                ext = filename.split('.')[-1].lower()
                if ext == 'pdf':
                    mime_type = 'application/pdf'
                elif ext in ['jpg', 'jpeg']:
                    mime_type = 'image/jpeg'
                elif ext == 'png':
                    mime_type = 'image/png'
                else:
                    # Keep original if we can't guess, but Gemini might reject it
                    mime_type = mime_type or 'application/octet-stream'

                logger.debug(f"Detected mime type for {filename}: {mime_type}")

            parts.append(f"\n--- File: {filename} ---\n")
            parts.append(Part.from_data(data=content, mime_type=mime_type))

            logger.info(f"File {i+1} ({filename}) added to the request parts")

        logger.info(f"Sending request to Gemini API with {len(parts)} total parts")

        try:
            # Generation config to enforce JSON if possible, or just rely on prompt
            # Gemini 1.5 Pro supports response_mime_type="application/json"
            response = self.model.generate_content(
                parts,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": 0.0, # Deterministic
                }
            )

            if response.candidates and response.candidates[0].finish_reason != FinishReason.STOP:
                logger.warning(f"Gemini API response did not finish with STOP reason. Finish reason: {response.candidates[0].finish_reason}")
                # Handle cases where it was blocked or max tokens reached
            else:
                logger.info("Gemini API response received successfully")

            json_str = response.text
            logger.debug(f"Raw Gemini response length: {len(json_str)} characters")

            # Clean up markdown code blocks if present (though response_mime_type should handle it)
            original_json_str = json_str
            if json_str.startswith("```json"):
                json_str = json_str[7:]
                logger.debug("Removed opening markdown json block")
            if json_str.endswith("```"):
                json_str = json_str[:-3]
                logger.debug("Removed closing markdown block")

            if original_json_str != json_str:
                logger.debug(f"Cleaned JSON response length: {len(json_str)} characters")

            logger.debug(f"Parsing JSON response: {json_str[:200]}...")

            data = json.loads(json_str)
            logger.info(f"Successfully parsed JSON response with {len(data)} top-level keys")

            # Validate with Pydantic
            logger.debug("Validating response with Pydantic schema...")
            validated_data = schema_class(**data)
            logger.info("Pydantic validation passed successfully")

            # Extract token usage information
            token_usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                token_usage = {
                    'prompt_token_count': response.usage_metadata.prompt_token_count,
                    'candidates_token_count': response.usage_metadata.candidates_token_count,
                    'total_token_count': response.usage_metadata.total_token_count,
                }
                logger.info(f"Token usage - Prompt: {token_usage['prompt_token_count']}, "
                          f"Response: {token_usage['candidates_token_count']}, "
                          f"Total: {token_usage['total_token_count']}")

            result = validated_data.model_dump()
            result['_token_usage'] = token_usage

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Gemini: {str(e)}")
            logger.debug(f"Raw response that failed parsing: {response.text if 'response' in locals() else 'Response not available'}")
            raise ExtractionError(f"Failed to parse JSON response from Gemini: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini extraction failed: {str(e)}", exc_info=True)
            raise ExtractionError(f"Gemini extraction failed: {str(e)}")

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