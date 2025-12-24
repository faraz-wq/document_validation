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
        
        # 0. Ingest AI-identified errors (Validation notes from the 4-step AI workflow)
        ai_errors = extraction_summary.get("_errors", [])
        for err in ai_errors:
            if isinstance(err, dict):
                issues.append(VerificationIssue(
                    field=err.get("field"),
                    severity=err.get("severity", "error"),
                    message=err.get("message", "AI detected an issue"),
                    passed=False
                ))

        # 1. Verify Key Details (Mandatory checks + Proof checks)
        for detail in config.key_details:
            detail_issues = self._verify_key_detail(extraction_summary, detail)
            issues.extend(detail_issues)
            
        # 2. Verify Business Rules (Consistency + Logic)
        for rule in config.rules:
            rule_issues = self._verify_rule(extraction_summary, rule)
            issues.extend(rule_issues)
            
        # Determine overall status and dynamic confidence score
        total_checks = len(issues)
        failed_checks = [i for i in issues if not i.passed]
        passed_checks_count = total_checks - len(failed_checks)
        
        # Heuristic: Critical errors (severity=error) have more weight
        error_count = len([i for i in failed_checks if i.severity == "error"])
        warning_count = len([i for i in failed_checks if i.severity == "warning"])
        
        # Confidence score calculation
        if total_checks > 0:
            # Base score is percentage of passed checks
            base_score = passed_checks_count / total_checks
            # Subtract penalty for unresolved errors
            confidence_score = max(0.1, base_score - (error_count * 0.1))
        else:
            confidence_score = 1.0

        # Merge Engine Issues into field_remarks for field-level "notes"
        field_remarks = extraction_summary.get("field_remarks", {}).copy()
        for issue in issues:
            if not issue.passed and issue.field:
                msg = issue.message
                # Clean up "Note:" or "Note: Note:" prefixing
                if msg.startswith("Note:"):
                    msg = msg[5:].strip()
                if msg.startswith("Note:"): # Double prefix
                    msg = msg[5:].strip()
                
                existing = field_remarks.get(issue.field, "")
                if existing:
                    # Deduplicate common phrases
                    if msg.lower() not in existing.lower():
                        field_remarks[issue.field] = f"{existing} | {msg}"
                else:
                    field_remarks[issue.field] = f"Note: {msg}"

        status = "verified" if error_count == 0 else "flagged"
        
        # Build dynamic summary
        if error_count == 0 and warning_count == 0:
            summary = f"Successfully verified {total_checks} data points across all source documents."
        else:
            inconsistency_count = len([i for i in failed_checks if any(kw in i.message.lower() for kw in ["mismatch", "consistent", "variation", "different"])])
            summary = f"Validation found {error_count} errors and {warning_count} warnings."
            if inconsistency_count > 0:
                summary += f" {inconsistency_count} cross-document inconsistencies were detected."
            
        confidence_reason = f"Verification check passed {passed_checks_count}/{total_checks} validation tests."
        
        return VerificationReport(
            application_type=config.application_type,
            report_id=f"VR_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            overall_status=status,
            issues=issues,
            extraction_summary=extraction_summary,
            field_remarks=field_remarks, # Passed to frontend as field notes
            bounding_boxes=extraction_summary.get("bounding_boxes", {}),
            citations=extraction_summary.get("citations", {}),
            source_documents=extraction_summary.get("source_documents", []),
            page_text=extraction_summary.get("page_text", {}),
            confidence_score=round(confidence_score, 2),
            summary=summary,
            confidence_reason=confidence_reason,
            metadata={
                "total_issues": len(issues),
                "passed_count": passed_checks_count,
                "error_count": error_count,
                "warning_count": warning_count,
                "confidence_score": round(confidence_score, 2),
                "confidence_reason": confidence_reason
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
            # We use bounding_boxes as the primary source for proof verification 
            # because they are already resolved to pages and have document_title attached.
            bboxes = summary.get("bounding_boxes", {}).get(detail.field_path, [])
            found_proofs = set()
            
            for box in bboxes:
                # Document title and type (AI provides title in bounding box resolution)
                title = box.get("document_title")
                if title:
                    found_proofs.add(title)
            
            # Fallback: Check citations if bounding boxes are missing or incomplete
            if not found_proofs:
                citations = summary.get("citations", {})
                field_cites = self._get_citations_for_field(citations, detail.field_path)
                source_docs = summary.get("source_documents", [])
                doc_map = {}
                for doc in source_docs:
                    fname = doc.get("filename")
                    dtype = doc.get("document_title") or doc.get("document_type")
                    pnums = doc.get("page_numbers", [])
                    if isinstance(pnums, (int, str)): pnums = [pnums]
                    for p in pnums:
                        doc_map[(fname, int(p))] = dtype
                
                for cite in field_cites:
                    match = re.search(r"^(.*?) \(Page (\d+)\)", cite)
                    if match:
                        fname, pnum = match.group(1), int(match.group(2))
                        dtype = doc_map.get((fname, pnum))
                        if dtype: found_proofs.add(dtype)

            # Check if any found proof matches valid proof docs (Fuzzy + Keyword)
            is_verified = False
            for req_doc in detail.valid_proof_documents:
                req_doc_lower = req_doc.lower()
                req_keywords = {w.lower() for w in re.findall(r'\w+', req_doc) if len(w) > 3}
                
                for found_doc in found_proofs:
                    found_doc_lower = found_doc.lower()
                    # 1. Direct fuzzy match
                    if difflib.SequenceMatcher(None, req_doc_lower, found_doc_lower).ratio() >= 0.7:
                        is_verified = True
                        break
                    
                    # 2. Keyword intersection (e.g., 'Aadhar' vs 'Aadhaar')
                    found_keywords = {w.lower() for w in re.findall(r'\w+', found_doc) if len(w) > 2}
                    # Substring check for keywords to handle spelling variations like Aadhar/Aadhaar
                    if any(rk[:5] in fk or fk[:5] in rk for rk in req_keywords for fk in found_keywords if len(rk) >= 5 and len(fk) >= 5):
                        is_verified = True
                        break
                    if any(rk in found_doc_lower for rk in req_keywords if len(rk) > 3):
                        is_verified = True
                        break
                        
                if is_verified: break
            
            if not is_verified:
                # Check if we found ANY proof, just not the RIGHT proof
                proof_list = ", ".join(list(found_proofs)[:3])
                msg = f"Note: Valid proof (e.g. {', '.join(detail.valid_proof_documents[:2])}) not found."
                if found_proofs:
                    msg += f" Found '{proof_list}' instead."
                else:
                    msg += " No supporting documentation identified for this field."
                
                issues.append(VerificationIssue(
                    field=detail.field_path,
                    severity="warning",
                    message=msg,
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
