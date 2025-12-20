import re
import difflib
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.verification.schema import (
    VerificationConfig, 
    VerificationReport, 
    VerificationIssue, 
    KeyDetailDefinition, 
    ValidationRuleDefinition
)
from app.logging_config import get_logger

logger = get_logger(__name__)

class VerificationEngine:
    """
    The NEW core verification engine. 
    Does not use any legacy validation code.
    Uses only 'Key Details' and 'Rules' definitions.
    """
    
    def verify(self, extraction_summary: Dict[str, Any], config: VerificationConfig) -> VerificationReport:
        logger.info(f"Starting NEW verification for: {config.application_type}")
        
        issues: List[VerificationIssue] = []
        
        # 1. Verify Key Details (Mandatory checks + Proof checks)
        for detail in config.key_details:
            detail_issues = self._verify_key_detail(extraction_summary, detail)
            issues.extend(detail_issues)
            
        # 2. Verify Business Rules (Consistency + Logic)
        for rule in config.rules:
            rule_issues = self._verify_rule(extraction_summary, rule)
            issues.extend(rule_issues)
            
        # Determine overall status
        error_count = len([i for i in issues if i.severity == "error" and not i.passed])
        status = "verified" if error_count == 0 else "flagged"
        if error_count > 3: status = "failed"
        
        return VerificationReport(
            application_type=config.application_type,
            report_id=f"VR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            overall_status=status,
            issues=issues,
            extraction_summary=extraction_summary,
            bounding_boxes=extraction_summary.get("bounding_boxes", {}),
            citations=extraction_summary.get("citations", {}),
            source_documents=extraction_summary.get("source_documents", []),
            metadata={
                "total_issues": len(issues),
                "error_count": error_count
            }
        )

    def _verify_key_detail(self, summary: Dict[str, Any], detail: KeyDetailDefinition) -> List[VerificationIssue]:
        issues = []
        value = self._get_value(summary, detail.field_path)
        
        # A. Completeness Check
        if not value and detail.is_mandatory:
            issues.append(VerificationIssue(
                field=detail.field_path,
                severity="error",
                message=f"Mandatory detail '{detail.display_name}' could not be identified",
                passed=False
            ))
            return issues # Skip proof if missing

        # B. Proof Coverage Check
        if value and detail.valid_proof_documents:
            citations = summary.get("citations", {})
            source_docs = summary.get("source_documents", [])
            
            # Map of (file, page) -> doc_type
            doc_map = {}
            for doc in source_docs:
                fname = doc.get("filename")
                dtype = doc.get("document_title")
                for p in doc.get("page_numbers", []):
                    doc_map[(fname, p)] = dtype
            
            # Find which docs proved THIS field
            found_proofs = set()
            field_cites = self._get_citations_for_field(citations, detail.field_path)
            
            for cite in field_cites:
                match = re.search(r"^(.*?) \(Page (\d+)\)", cite)
                if match:
                    fname, pnum = match.group(1), int(match.group(2))
                    dtype = doc_map.get((fname, pnum))
                    if dtype: found_proofs.add(dtype)
            
            # Check if any found proof matches valid proof docs
            is_verified = False
            for req_doc in detail.valid_proof_documents:
                if any(difflib.SequenceMatcher(None, req_doc.lower(), f.lower()).ratio() >= 0.8 for f in found_proofs):
                    is_verified = True
                    break
            
            if not is_verified:
                issues.append(VerificationIssue(
                    field=detail.field_path,
                    severity="error",
                    message=f"'{detail.display_name}' lacks valid proof. Expected: {', '.join(detail.valid_proof_documents)}",
                    passed=False
                ))
        
        return issues

    def _verify_rule(self, summary: Dict[str, Any], rule: ValidationRuleDefinition) -> List[VerificationIssue]:
        issues = []
        
        if rule.rule_id == "name_consistency":
            # 1. Check AI-noted inconsistencies
            errors = summary.get("_errors", [])
            for err in errors:
                if isinstance(err, dict) and any(f in err.get("field", "") for f in rule.fields_involved):
                    msg = err.get("message", "").lower()
                    if any(kw in msg for kw in ["match", "different", "spelling", "variation"]):
                        issues.append(VerificationIssue(
                            rule_id=rule.rule_id,
                            field=rule.fields_involved[0],
                            severity=rule.severity,
                            message=f"Name Inconsistency: {err.get('message')}",
                            passed=False
                        ))
            
            # 2. Automated Cross-Document Fuzzy Check
            target_value = self._get_value(summary, rule.fields_involved[0])
            if target_value and isinstance(target_value, str):
                citations = summary.get("citations", {})
                all_found_names = []
                
                field_cites = self._get_citations_for_field(citations, rule.fields_involved[0])
                for cite in field_cites:
                    match = re.search(r" - (.*)$", cite)
                    if match: all_found_names.append(match.group(1).strip())

                for name in all_found_names:
                    ratio = difflib.SequenceMatcher(None, target_value.lower(), name.lower()).ratio()
                    if ratio < 0.9 and ratio > 0.4:
                        issues.append(VerificationIssue(
                            rule_id=rule.rule_id,
                            field=rule.fields_involved[0],
                            severity=rule.severity,
                            message=f"Spelling variation detected across documents: '{target_value}' vs '{name}'",
                            passed=False
                        ))
                        break
        
        elif rule.rule_type == "proof_existence":
            # This is largely covered by _verify_key_detail proof check, 
            # but can be used for secondary cross-references
            pass
            
        return issues

    def _get_value(self, obj: Any, path: str) -> Any:
        parts = path.replace("[", ".").replace("]", "").split(".")
        current = obj
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except:
                    return None
            else:
                return None
        return current

    def _get_citations_for_field(self, citations: Dict[str, Any], path: str) -> List[str]:
        # Dotted notation citations lookup
        parts = path.replace("[", ".").replace("]", "").split(".")
        current = citations
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return []
        
        if isinstance(current, list): return current
        if isinstance(current, str): return [current]
        return []
