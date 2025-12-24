import os
import json
import re
import difflib
from typing import List, Dict, Any, Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from app.verification.schema import VerificationConfig, KeyDetailDefinition
from app.ocr.google_vision import perform_ocr
from app.utils.recorder import save_record
from app.logging_config import get_logger

logger = get_logger(__name__)

class VerificationProcessor:
    """
    The NEW Agnostic AI Processor.
    Handles extraction based solely on VerificationConfig (Key Details).
    Does NOT use pydantic models for the extraction result, ensuring no crashes on missing data.
    """
    
    def __init__(self):
        # Initialize Vertex AI from env
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if project_id:
            vertexai.init(project=project_id, location=location)
        
        self.model = GenerativeModel("gemini-1.5-pro")

    def process(self, app_type: str, files: List[Dict[str, Any]], config: VerificationConfig) -> Dict[str, Any]:
        logger.info(f"Starting agnostic extraction for: {app_type}")
        
        from concurrent.futures import ThreadPoolExecutor
        
        # 1. Parallel OCR Phase
        all_blocks_indexed = {}
        all_page_texts = {}
        file_texts = []
        
        def ocr_and_index(file_idx, file_data):
            filename = file_data['filename']
            content = file_data['content']
            mime_type = file_data.get('mime_type', 'application/pdf')
            
            try:
                pages_output = perform_ocr(content, mime_type)
                save_record("ocr", {"filename": filename, "ocr_data": pages_output}, f"ocr_{filename}")
                
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

        with ThreadPoolExecutor(max_workers=min(len(files), 5)) as executor:
            futures = [executor.submit(ocr_and_index, i, f) for i, f in enumerate(files, start=1)]
            for f in futures:
                txt, blocks, p_texts = f.result()
                file_texts.append(txt)
                all_blocks_indexed.update(blocks)
                all_page_texts.update(p_texts)

        # 2. Build Dynamic Prompt
        prompt = self._build_prompt(config)
        parts = [prompt] + file_texts
        
        # 3. AI Intelligence Phase
        logger.info(f"Sending request to Gemini with structured context")
        response = self.model.generate_content(
            parts,
            generation_config={"response_mime_type": "application/json", "temperature": 0.0}
        )
        
        raw_text = response.text
        save_record("gemini_raw", {"response": raw_text, "app_type": app_type}, f"raw_{app_type}")
        
        try:
            if raw_text.startswith("```json"): raw_text = raw_text[7:]
            if raw_text.endswith("```"): raw_text = raw_text[:-3]
            data = json.loads(raw_text)
        except Exception as e:
            logger.error(f"Failed to parse Gemini JSON: {e}")
            raise ValueError(f"AI returned invalid JSON: {str(e)}")

        # 4. Post-Process
        block_mapping = data.pop('_block_ids_mapping', {})
        source_docs = data.get('source_documents', [])
        
        # 5. Coordinate Resolution & Normalization
        result = data.copy()
        result['bounding_boxes'] = self._resolve_boxes(data, all_blocks_indexed, block_mapping, source_docs)
        self._normalize_dates(result)
        
        if hasattr(response, 'usage_metadata'):
            result['_token_usage'] = {'total_token_count': response.usage_metadata.total_token_count}
        
        result['page_text'] = all_page_texts
        
        save_record("extraction_final", result, f"final_{app_type}")
        return result

    def _normalize_dates(self, data: Dict[str, Any]):
        """Recursively find and normalize date strings to YYYY-MM-DD"""
        date_patterns = [
            (r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', '%d-%m-%Y'), # DD-MM-YYYY
            (r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', '%Y-%m-%d'), # YYYY-MM-DD
        ]
        
        def normalize_str(s):
            if not isinstance(s, str): return s
            # Skip short strings or strings that clearly aren't dates
            if len(s) < 8 or len(s) > 15: return s
            
            for pattern, fmt in date_patterns:
                match = re.search(pattern, s)
                if match:
                    try:
                        # Attempt to parse
                        from datetime import datetime
                        d_str = match.group(0).replace('/', '-')
                        if fmt == '%d-%m-%Y':
                            d = datetime.strptime(d_str, '%d-%m-%Y')
                        else:
                            d = datetime.strptime(d_str, '%Y-%m-%d')
                        return d.strftime('%Y-%m-%d')
                    except:
                        continue
            return s

        def traverse(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if 'date' in k.lower() or 'dob' in k.lower():
                        obj[k] = normalize_str(v)
                    else:
                        traverse(v)
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item)

        traverse(data)

    def _build_prompt(self, config: VerificationConfig) -> str:
        fields_str = "\n".join([f"- {d.field_path}: {d.description} (Proof docs: {', '.join(d.valid_proof_documents)})" for d in config.key_details])
        
        return f"""
        Extract and validate document data based on the following 4-step workflow.
        
        TARGET SCHEMA (Fields to extract):
        {fields_str}
        
        STEP 1: DOCUMENT RECOGNITION (Per Page)
        Examine every page thoroughly. Identify the document type (e.g., Aadhaar Card, Passport, Application Form, Salary Slip).
        Populate the 'source_documents' array for EVERY page. Cross-reference with the 'Proof docs' list below to ensure you use standard names (e.g., use "Aadhaar Card" if it matches).
        
        STEP 2: EXTRACTION & SPATIAL MAPPING
        - For each TARGET FIELD, search for values across ALL pages. Capture even if the value repeats.
        - Capture the EXACT text segments.
        - BUILD BOUNDING BOXES: Provide the structured block IDs (e.g., ["F1P1B1"]) for EVERY occurrence of the value found. 
          If you find the applicant name on the Application Form AND the Aadhaar Card, you MUST include block IDs from BOTH pages.
        
        STEP 3: CROSS-PAGE CONSISTENCY ANALYSIS
        - Compare values for the same field (e.g., Name, Date of Birth, ID Number) found across different pages and documents.
        - Identify ANY inconsistencies, spelling variations, or mismatches.
        - If the extracted value differs across documents, use the most "authoritative" one for the main JSON field, but list the mismatch in '_errors'.
        
        STEP 4: SCHEMA & LOGIC VALIDATION
        - Take the TARGET SCHEMA and validate the results.
        - Note any missing mandatory fields.
        - Verify if the provided documents satisfy the 'Proof docs' requirements for each field.
        
        OUTPUT FORMAT:
        Return ONLY valid JSON:
        {{
          "app_type": "{config.application_type}",
          ... all fields from TARGET SCHEMA ...,
          "source_documents": [
            {{ 
              "filename": "...", 
              "document_title": "...", 
              "page_numbers": [...],
              "document_type": "...",
              "summary": "Short description of what is on this page"
            }}
          ],
          "citations": {{ "field_path": ["Filename (Page X) - <Text>", ...], ... }},
          "_block_ids_mapping": {{ "field_path": ["F1P1B1", ...], ... }},
          "_errors": [
            {{ 
              "field": "field_path", 
              "message": "Detailed explanation of mismatch or validation failure", 
              "severity": "error|warning",
              "type": "inconsistency|missing|format|invalid_proof"
            }}
          ]
        }}
        """

    def _resolve_boxes(self, data, indexed_blocks, mapping, source_docs) -> Dict[str, List[Dict[str, Any]]]:
        resolved = {}
        
        # Normalize filenames for robust matching
        def norm_fn(fn):
            if not fn: return ""
            return os.path.basename(str(fn)).lower()

        # Map (filename, pnum) to best available title/type
        doc_map = {}
        for d in source_docs:
            fname = norm_fn(d.get('filename'))
            title = d.get('document_title') or d.get('document_type') or "Unknown Document"
            pnums = d.get('page_numbers', [])
            if isinstance(pnums, (int, str)): pnums = [pnums]
            for p in pnums:
                try:
                    pnum = int(p)
                    doc_map[(fname, pnum)] = title
                    # Fallback for when AI omits filename in source_documents
                    if "" not in doc_map or pnum not in [k[1] for k in doc_map if k[0] == ""]:
                        doc_map[("", pnum)] = title
                except:
                    continue

        def get_all_paths(obj, current_path=""):
            paths = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_path = f"{current_path}.{k}" if current_path else k
                    paths.extend(get_all_paths(v, new_path))
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    new_path = f"{current_path}[{i}]"
                    paths.extend(get_all_paths(v, new_path))
            else:
                paths.append(current_path)
            return paths

        all_field_paths = get_all_paths(data)
        
        for path in all_field_paths:
            bids = mapping.get(path, [])
            if isinstance(bids, str): bids = [bids]
            
            boxes = []
            for bid in bids:
                if bid in indexed_blocks:
                    block = indexed_blocks[bid]
                    fn = norm_fn(block['filename'])
                    pn = int(block['page'])
                    
                    # Try exact match (normalized filename + page)
                    title = doc_map.get((fn, pn))
                    
                    # Try wildcard match (any filename + page)
                    if not title:
                        title = doc_map.get(("", pn))
                    
                    # Last resort fallback if still not found
                    if not title: title = "Unknown Document"
                    
                    boxes.append({
                        "filename": block['filename'],
                        "page": pn,
                        "coordinates": block['bbox_px'],
                        "document_title": title
                    })
            
                resolved[path] = boxes
                
        return resolved
