import os
import json
import re
import difflib
import time
from typing import List, Dict, Any, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from app.verification.schema import VerificationConfig, KeyDetailDefinition
from app.ocr.google_vision import perform_ocr
from app.utils.recorder import save_record
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ServiceUnavailable, InternalServerError
from app.logging_config import get_logger

logger = get_logger(__name__)

class VerificationProcessor:
    """
    The NEW Agnostic AI Processor implementing the Universal Extraction Workflow.
    
    Workflow Stages:
    1. Page & Document Identification
    2. Schema-Agnostic Field Extraction (Universal)
    3. Field Entity Construction
    4. Field Relationship Modeling
    5. Schema Projection (Final Step)
    6. Validation & Issues
    """
    
    def __init__(self):
        # Initialize Vertex AI from env
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if project_id:
            vertexai.init(project=project_id, location=location)
        
        self.model = GenerativeModel("gemini-2.5-flash")

    def process(self, app_type: str, files: List[Dict[str, Any]], config: VerificationConfig) -> Dict[str, Any]:
        logger.info(f"Starting Universal Extraction for: {app_type}")
        
        from concurrent.futures import ThreadPoolExecutor
        
        # 1. Parallel OCR Phase (Preserve existing logic)
        all_blocks_indexed = {}
        all_page_texts = {}
        file_texts = []
        
        def ocr_and_index(file_idx, file_data):
            filename = file_data['filename']
            content = file_data['content']
            mime_type = file_data.get('mime_type', 'application/pdf')
            
            try:
                pages_output = perform_ocr(content, mime_type)
                # RECORD RAW OCR OUTPUT (AS RETURNED BY OCR SERVICE)
                save_record("ocr_raw", {"filename": filename, "ocr_data": pages_output}, f"ocr_{filename}")
                
                txt = f"\n### FILE {file_idx}: {filename} ###\n"
                local_blocks = {}
                local_page_texts = {}
                
                for p_idx, page in enumerate(pages_output, start=1):
                    pnum = page['page']
                    txt += f"\n[PAGE {pnum}]\n"
                    page_content = ""
                    for b_idx, block in enumerate(page['blocks']):
                        # Structured key: F{file}_P{page}_B{block}
                        bid = f"F{file_idx}P{pnum}B{b_idx}"
                        txt += f"[{bid}] {block['text']}\n"
                        page_content += f"{block['text']}\n"
                        local_blocks[bid] = {
                            **block,
                            'page': pnum,
                            'filename': filename,
                            'width': page['image_width'],
                            'height': page['image_height']
                        }
                    local_page_texts[f"{filename}_page_{pnum}"] = page_content
                    
                return txt, local_blocks, local_page_texts
            except Exception as e:
                logger.error(f"OCR failed for {filename}: {e}")
                return f"\n[ERROR OCRing {filename}]\n", {}, {}

        # Run OCR
        with ThreadPoolExecutor(max_workers=min(len(files), 5)) as executor:
            futures = [executor.submit(ocr_and_index, i, f) for i, f in enumerate(files, start=1)]
            for f in futures:
                txt, blocks, p_texts = f.result()
                file_texts.append(txt)
                all_blocks_indexed.update(blocks)
                all_page_texts.update(p_texts)

        # 2. Build Dynamic Workflow Prompt
        prompt = self._build_prompt(config)
        parts = [prompt] + file_texts
        
        # 3. AI Intelligence Phase
        logger.info(f"Sending Universal Extraction request to Gemini")
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((ServiceUnavailable, InternalServerError)),
            before_sleep=lambda retry_state: logger.warning(f"AI Extraction failed, retrying... (Attempt {retry_state.attempt_number})")
        )
        def generate_with_retry():
            return self.model.generate_content(
                parts,
                generation_config={
                    "response_mime_type": "application/json", 
                    "temperature": 0.0,
                }
            )

        try:
            response = generate_with_retry()
        except Exception as e:
            logger.error(f"AI Extraction failed after retries: {str(e)}")
            raise
        
        raw_text = response.text
        # RECORD RAW GEMINI OUTPUT
        save_record("gemini_raw", {"raw_text": raw_text, "app_type": app_type}, f"raw_{app_type}")
        
        # Also save as a text file for complete raw visibility if it's large
        try:
            raw_log_path = os.path.join("records", "gemini_raw", f"raw_{app_type}_{int(time.time())}.txt")
            os.makedirs(os.path.dirname(raw_log_path), exist_ok=True)
            with open(raw_log_path, "w", encoding="utf-8") as f:
                f.write(raw_text)
        except Exception:
            pass
        
        try:
            # Clean up markdown code blocks
            if raw_text.startswith("```json"): 
                raw_text = raw_text[7:]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]
            if raw_text.endswith("```"): 
                raw_text = raw_text[:-3]
            
            raw_text = raw_text.strip()
            
            # Try to parse directly first
            try:
                ai_data = json.loads(raw_text)
                # Record parsed but un-resolved outcome
                save_record("gemini_parsed", ai_data, f"parsed_{app_type}")
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues and truncated response
                logger.warning(f"Initial JSON parse failed: {e}. Attempting to repair truncated JSON...")
                
                fixed_text = self._repair_json(raw_text)
                
                try:
                    ai_data = json.loads(fixed_text)
                    logger.info("Successfully parsed JSON after repair")
                    save_record("gemini_parsed", ai_data, f"parsed_{app_type}")
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON parsing failed even after repair: {e2}")
                    logger.error(f"Error at position {e2.pos}: {fixed_text[max(0, e2.pos-50):min(len(fixed_text), e2.pos+50)]}")
                    
                    save_record("gemini_error", {
                        "response": raw_text,
                        "fixed_response": fixed_text,
                        "error": str(e2),
                        "position": e2.pos,
                        "app_type": app_type
                    }, f"error_{app_type}")
                    
                    raise ValueError(f"AI returned invalid JSON: {str(e2)}")
                    
        except Exception as e:
            if not isinstance(e, ValueError):
                logger.error(f"Failed to parse Gemini JSON: {e}")
                raise ValueError(f"AI returned invalid JSON: {str(e)}")
            raise

        # 4. Post-Process: Resolve Citations and Normalize
        # The AI returns block IDs in field_value or citations. We need to attach coordinates.
        self._resolve_citations(ai_data, all_blocks_indexed)
        
        # Implement Goal 10: Structured Document/Page storage
        structured_docs = []
        doc_names = set(f['filename'] for f in files)
        for fname in doc_names:
            pages = []
            # Gather pages for this document from OCR results
            # all_page_texts keys are "filename_page_N"
            pattern = re.compile(rf"^{re.escape(fname)}_page_(\d+)$")
            for key, text in all_page_texts.items():
                match = pattern.match(key)
                if match:
                    pnum = int(match.group(1))
                    # Determine roles (simple heuristic)
                    role = "application_form" if "form" in fname.lower() or "app" in fname.lower() else "supporting_document"
                    pages.append({
                        "page_number": pnum,
                        "text": text,
                        "role": role
                    })
            
            # Sort pages
            pages.sort(key=lambda x: x['page_number'])
            
            structured_docs.append({
                "filename": fname,
                "document_type": pages[0]["role"] if pages else "unknown",
                "pages": pages
            })

        ai_data['documents'] = structured_docs
        
        # Add metadata
        if 'metadata' not in ai_data:
            ai_data['metadata'] = {}
        ai_data['metadata']['app_type'] = app_type
        if hasattr(response, 'usage_metadata'):
             ai_data['metadata']['token_usage'] = {'total_token_count': response.usage_metadata.total_token_count}
        
        save_record("extraction_final", ai_data, f"final_{app_type}")
        return ai_data

    def _repair_json(self, text: str) -> str:
        """
        Attempts to repair truncated or malformed JSON by balancing braces/brackets
        and closing open strings.
        """
        if not text:
            return "{}"
            
        text = text.strip()
        
        stack = []
        in_string = False
        escaped = False
        
        fixed_chars = []
        
        for char in text:
            if in_string:
                if char == '\\' and not escaped:
                    escaped = True
                elif char == '"' and not escaped:
                    in_string = False
                else:
                    escaped = False
            else:
                if char == '"':
                    in_string = True
                elif char == '{':
                    stack.append('}')
                elif char == '[':
                    stack.append(']')
                elif char == '}':
                    if stack and stack[-1] == '}':
                        stack.pop()
                elif char == ']':
                    if stack and stack[-1] == ']':
                        stack.pop()
            fixed_chars.append(char)
            
        fixed_text = "".join(fixed_chars)
        
        # Close open string
        if in_string:
            # If the string ends with an unclosed escape sequence (e.g., "val\),
            # remove the backslash to make it a valid string.
            if fixed_text.endswith('\\') and escaped:
                fixed_text = fixed_text[:-1]
            fixed_text += '"'
            
        # Remove trailing comma before closing
        fixed_text = fixed_text.rstrip()
        if fixed_text.endswith(','):
            fixed_text = fixed_text[:-1]
            
        # Close open structures
        while stack:
            fixed_text += stack.pop()
            
        return fixed_text



    def _build_prompt(self, config: VerificationConfig) -> str:
        # Prepare schema details
        schema_json = json.dumps([d.dict() for d in config.key_details], indent=2)
        
        return f"""
You are a document extraction and validation engine for government service applications.
Your task is to extract fields defined in the schema, model their relationships, and validate them.

🔒 Non-Negotiable Rules (Read Carefully)
- ONLY extract fields that are present in the provided schema or are essential for validating those fields.
- DO NOT extract irrelevant data (e.g., generic instructions, unrelated fine print).
- Target ONLY information that helps fulfill the required fields listed in the schema.
- Every detected fact becomes a field entity.
- Schema fields are derived from these entities.
- Never output flat key–value maps.
- All reasoning must be explicit via field relationships.
- Output MUST strictly follow the response JSON schema described below.
- BE CONCISE: Keep 'description' and 'reasoning' fields extremely short (max 1 sentence).
- If you hit token limits, prioritize completing the JSON structure over adding more fields.
- Violation of any rule is an error.

🧠 Processing Stages (Must be followed in order)
Stage 1 — Page & Document Identification
- Identify each document and page.
- Assign document type (e.g., Application Form, Aadhaar Card, Rice Card).
- Preserve filename, page number, and document role.

Stage 2 — Schema-Focused Field Extraction
- For every page of every document, extract ONLY the fields relevant to the schema.
- Extract fields from the Application Form ('application_claim') and supporting documents ('proof').
- Each extracted field MUST be emitted as an independent field entity.
- IMPORTANT: If there are many repetitive documents (e.g. many Aadhaar cards), summarize them concisely.

Stage 3 — Field Entity Construction
- Create field entities with unique IDs (fe_xxx).
- Role: 'application_claim' (from Form), 'proof' (from Supporting Docs), 'contextual' (metadata).
- POPULATE 'validation_requirements' for 'application_claim' role: list specific proofs required and validation rules (e.g. name_match).
- POPULATE 'supports' for 'proof' role: explicit list of which application field it supports.

Stage 4 — Field Relationship Modeling
- Create explicit relationships between field entities: supports, contradicts, duplicates, derives.

Stage 5 — Schema Projection (FINAL STEP)
- APPLY THIS SCHEMA: 
{schema_json}
- Derive schema fields from one or more field entities (using 'derived_from' list).
- Compute final values, confidence, and reasoning.
- DO NOT include unmapped or irrelevant fields in the final output.

Stage 6 — Validation & Issues
- Validate ONLY schema-projected fields against the schema rules.
- Issues must reference 'schema_field' and 'related_field_ids'.
- DO NOT OUTPUT RAW VALUES IN ISSUES.
- If a value is missing or there is a conflict/mismatch between documents, use the phrase "unable to find" in the message. DO NOT explicitly use the word "mismatch".

📦 REQUIRED OUTPUT JSON SCHEMA
You MUST output valid JSON with exactly the following top-level keys:
{{
  "application_type": "{config.application_type}",
  "documents": [],
  "field_entities": [],
  "field_relationships": [],
  "schema_projection": {{
     "schema_name": "...",
     "ordered_fields": []
  }},
  "validation_summary": {{}},
  "issues": [],
  "metadata": {{}}
}}

🧩 Field Entity Schema (Strict)
{{
  "field_id": "fe_unique_id",
  "field_name": "raw_extracted_key",
  "field_value": "extracted value",
  "document": {{ "filename": "...", "document_type": "...", "page": 0 }},
  "citation": {{ "bounding_box": ["F1P1B1"], "text_snippet": "..." }},
  "description": "...",
  "role": "application_claim | proof | contextual",
  "validation_requirements": {{
    "required_proofs": ["Aadhaar Card"],
    "rules": ["name_match"]
  }},
  "supports": [
    {{ "application_field": "applicant.name", "support_type": "identity_match" }}
  ],
  "confidence": 0.95
}}

🧩 Field Relationship Schema
{{
  "from_field_id": "fe_source",
  "to_field_id": "fe_target",
  "relationship": "supports | contradicts | duplicates | derives",
  "confidence": 0.9,
  "reason": "..."
}}

🧩 Schema Projection Schema
{{
  "schema_name": "{config.application_type}",
  "ordered_fields": [
    {{
      "schema_field": "schema_key",
      "value": "final_value",
      "derived_from": ["fe_claim", "fe_proof"],
      "confidence": 0.99,
      "reasoning": "Derived from claim validated by proof"
    }}
  ]
}}

🧩 Issues Schema (Strict - No Values)
{{
  "schema_field": "applicant.name",
  "severity": "error | warning",
  "message": "unable to find valid name in application form",
  "related_field_ids": ["fe_claim", "fe_proof"],
  "requires_review": true
}}

🧩 Validation Summary (Metrics Only)
{{
  "total_schema_fields": 10,
  "validated_fields": 8,
  "errors": 2,
  "warnings": 0,
  "confidence_score": 0.85
}}

🟢 Final Reminder
Focus ONLY on schema fields. Avoid irrelevant data. Structure as requested.
"""


    def _resolve_citations(self, ai_data: Dict[str, Any], all_blocks_indexed: Dict[str, Any]):
        """
        Resolves Block IDs (e.g., F1P1B12) in citations to actual pixel coordinates.
        Updates 'citation.bounding_box' in-place from list of IDs to list of [y, x, y, x] normalized to 1000.
        """
        
        def resolve_entity(entity):
            citation = entity.get('citation', {})
            if not citation: return
            
            bbox_ids = citation.get('bounding_box', [])
            
            # If the AI returned IDs (strings), resolve them
            if isinstance(bbox_ids, list) and len(bbox_ids) > 0 and isinstance(bbox_ids[0], str):
                resolved_boxes = []
                for bid in bbox_ids:
                    if bid in all_blocks_indexed:
                        block = all_blocks_indexed[bid]
                        raw_box = None
                        if 'bbox_px' in block:
                             raw_box = block['bbox_px']
                        elif 'vertices' in block:
                             v = block['vertices']
                             if len(v) >= 4:
                                 x_coords = [p.get('x', 0) for p in v]
                                 y_coords = [p.get('y', 0) for p in v]
                                 raw_box = [min(y_coords), min(x_coords), max(y_coords), max(x_coords)]
                        
                        if raw_box:
                            w = block.get('width', 1)
                            h = block.get('height', 1)
                            y_min, x_min, y_max, x_max = raw_box
                            
                            normalized = [
                                round((y_min / h) * 1000),
                                round((x_min / w) * 1000),
                                round((y_max / h) * 1000),
                                round((x_max / w) * 1000)
                            ]
                            resolved_boxes.append(normalized)
                
                citation['bounding_box'] = resolved_boxes

        # 1. Resolve Field Entities
        for entity in ai_data.get('field_entities', []):
            resolve_entity(entity)
            
        # 2. Resolve Unmapped Fields (might be duplicates/different instances)
        projection = ai_data.get('schema_projection', {})
        for entity in projection.get('unmapped_fields', []):
            resolve_entity(entity)
            
        # 3. Resolve Ordered Fields (if they contain internal entity objects - unlikely but safe)
        for field in projection.get('ordered_fields', []):
            # check if the AI nested an entity object (though prompt says derive_from)
            if isinstance(field.get('value'), dict) and 'citation' in field.get('value'):
                resolve_entity(field['value'])

