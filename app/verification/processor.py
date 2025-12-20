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
                for p_idx, page in enumerate(pages_output, start=1):
                    pnum = page['page']
                    txt += f"\n[PAGE {pnum}]\n"
                    for b_idx, block in enumerate(page['blocks']):
                        # Structured key: F{file}_P{page}_B{block}
                        bid = f"F{file_idx}P{pnum}B{b_idx}"
                        txt += f"[{bid}] {block['text']}\n"
                        local_blocks[bid] = {
                            **block,
                            'page': pnum,
                            'filename': filename,
                            'width': page['image_width'],
                            'height': page['image_height']
                        }
                return txt, local_blocks
            except Exception as e:
                logger.error(f"OCR failed for {filename}: {e}")
                return f"\n[ERROR OCRing {filename}]\n", {}

        with ThreadPoolExecutor(max_workers=min(len(files), 5)) as executor:
            futures = [executor.submit(ocr_and_index, i, f) for i, f in enumerate(files, start=1)]
            for f in futures:
                txt, blocks = f.result()
                file_texts.append(txt)
                all_blocks_indexed.update(blocks)

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
        Extract the following KEY DETAILS from the provided document blocks.
        
        TARGET FIELDS:
        {fields_str}
        
        RULES:
        1. Every page must be classified in 'source_documents' array with filename, document_title, and page_numbers.
        2. ENTITY IDENTIFICATION: In 'document_title', specify the owner if applicable (e.g., "Aadhaar Card - [Name]").
        3. Identify EXACT text segments for each field.
        4. SPATIAL PRECISION: For each field, provide the structured block IDs (e.g., ["F1P3B12", "F1P3B13"]) in a separate object called '_block_ids_mapping'. 
           ONLY include blocks that directly contain the value. The IDs MUST match the text markers exactly.
        5. If a field is not found, set its value to null. DO NOT guess.
        6. Provide citations for every field in a 'citations' object matching the field paths.
        7. Note any inconsistencies (e.g. name mismatch between documents) in an '_errors' array.
        
        OUTPUT FORMAT:
        Return ONLY valid JSON matching the field paths. Include:
        - All extracted fields
        - 'source_documents': [{{ "filename": "...", "document_title": "...", "page_numbers": [...] }}]
        - 'citations': {{ "field_path": "Filename (Page X) - <Text>", ... }}
        - '_block_ids_mapping': {{ "field_path": ["F#P#B#", "F#P#B#"], ... }}
        - '_errors': [{{ "field": "...", "message": "..." }}]
        """

    def _resolve_boxes(self, data, indexed_blocks, mapping, source_docs) -> Dict[str, List[Dict[str, Any]]]:
        resolved = {}
        
        # Map pnum to doc_title
        doc_map = {}
        for d in source_docs:
            for p in d.get('page_numbers', []):
                doc_map[(d.get('filename'), p)] = d.get('document_title')

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
                    boxes.append({
                        "filename": block['filename'],
                        "page": block['page'],
                        "coordinates": block['bbox_px'],
                        "document_title": doc_map.get((block['filename'], block['page']), "Unknown")
                    })
            
            if boxes:
                resolved[path] = boxes
                
        return resolved
