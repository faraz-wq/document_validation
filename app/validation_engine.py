"""
Generic validation engine for form-agnostic document validation.
This module implements the core validation logic that works across all application types.
"""

from typing import Dict, List, Any, Optional, Tuple
import difflib
import re
from app.validation_models import ValidationIssue, ValidationReport
from app.validation_rules import ValidationRuleSet, get_validation_rules
from app.validation.validators import (
    validate_required, 
    validate_date_format, 
    validate_aadhaar, 
    validate_income,
    generate_validation_summary_deterministic
)
from app.logging_config import get_logger

logger = get_logger(__name__)


class ValidationEngine:
    """
    Form-agnostic validation engine that validates extraction summaries
    against configurable rule sets.
    """
    
    def __init__(self, fuzzy_threshold: float = 0.85):
        """
        Initialize the validation engine.
        
        Args:
            fuzzy_threshold: Minimum similarity ratio for fuzzy matching (0.0 to 1.0)
        """
        self.fuzzy_threshold = fuzzy_threshold
        logger.info(f"ValidationEngine initialized with fuzzy_threshold={fuzzy_threshold}")
    
    def validate(
        self,
        application_type: str,
        extraction_summary: Dict[str, Any]
    ) -> ValidationReport:
        """
        Validate an extraction summary against the rules for the given application type.
        
        Args:
            application_type: The type of application being validated
            extraction_summary: The complete extraction summary from /extract-summary
            
        Returns:
            ValidationReport with auto_approved status, confidence score, and issues
        """
        logger.info(f"Starting validation for application_type: {application_type}")
        
        # Get validation rules for this application type
        rules = get_validation_rules(application_type)
        if not rules:
            logger.error(f"No validation rules found for application_type: {application_type}")
            raise ValueError(f"No validation rules configured for application type: {application_type}")
        
        issues: List[ValidationIssue] = []
        
        # Run all validation checks
        issues.extend(self._check_completeness(extraction_summary, rules))
        issues.extend(self._check_document_coverage(extraction_summary, rules))
        issues.extend(self._check_cross_field_consistency(extraction_summary, rules))
        issues.extend(self._check_proof_coverage(extraction_summary, rules))
        issues.extend(self._check_evidence_requirements(extraction_summary, rules))
        
        # Run custom validators if any
        if rules.custom_validators:
            for validator in rules.custom_validators:
                try:
                    custom_issues = validator(extraction_summary, rules)
                    if custom_issues:
                        issues.extend(custom_issues)
                except Exception as e:
                    logger.error(f"Custom validator failed: {e}", exc_info=True)
        
        # Calculate auto-approval and confidence
        auto_approved, confidence_score = self._calculate_approval_status(issues)
        
        # Generate summary (New deterministic approach)
        summary = generate_validation_summary_deterministic(issues, auto_approved)
        
        logger.info(f"Validation complete: auto_approved={auto_approved}, confidence={confidence_score:.2f}, issues={len(issues)}")
        
        return ValidationReport(
            auto_approved=auto_approved,
            confidence_score=confidence_score,
            issues=issues,
            summary=summary,
            metadata={
                "application_type": application_type,
                "rule_set_version": "1.0",
                "total_issues": len(issues),
                "error_count": sum(1 for i in issues if i.severity == "error"),
                "warning_count": sum(1 for i in issues if i.severity == "warning"),
                "info_count": sum(1 for i in issues if i.severity == "info")
            }
        )
    
    def _check_completeness(
        self,
        summary: Dict[str, Any],
        rules: ValidationRuleSet
    ) -> List[ValidationIssue]:
        """
        Check that all required fields are present and non-null.
        """
        logger.debug("Running completeness check")
        issues = []
        
        for field_path in rules.required_fields:
            value = self._get_nested_value(summary, field_path)
            
            if not validate_required(value):
                issues.append(ValidationIssue(
                    field=field_path,
                    severity="error",
                    message=f"Mandatory field '{field_path}' is missing or empty",
                    extracted_value=value,
                    expected_value="Present value",
                    requires_review=False
                ))
                logger.warning(f"Completeness check failed for field: {field_path}")
            
            # Special field validations if value IS present
            if value:
                # 1. Date validations
                if "date" in field_path.lower() or "dob" in field_path.lower():
                    if not validate_date_format(str(value)):
                        issues.append(ValidationIssue(
                            field=field_path,
                            severity="warning",
                            message=f"Invalid date format for '{field_path}': {value}",
                            extracted_value=value,
                            expected_value="DD/MM/YYYY",
                            requires_review=True
                        ))

                # 2. Aadhaar validations
                if "aadhaar" in field_path.lower():
                    if not validate_aadhaar(str(value)):
                        issues.append(ValidationIssue(
                            field=field_path,
                            severity="error",
                            message=f"Invalid Aadhaar number format: {value}",
                            extracted_value=value,
                            expected_value="12 digits",
                            requires_review=True
                        ))

                # 3. Income validations
                if "income" in field_path.lower():
                    if not validate_income(value):
                        issues.append(ValidationIssue(
                            field=field_path,
                            severity="warning",
                            message=f"Unusual income value detected for '{field_path}': {value}",
                            extracted_value=value,
                            expected_value="Numeric amount",
                            requires_review=True
                        ))
        
        logger.debug(f"Completeness check found {len(issues)} issues")
        return issues
    
    def _check_document_coverage(
        self,
        summary: Dict[str, Any],
        rules: ValidationRuleSet
    ) -> List[ValidationIssue]:
        """
        Verify that all required document types are present in source_documents.
        """
        logger.debug("Running document coverage check")
        issues = []
        
        source_documents = summary.get("source_documents", [])
        present_doc_types = set()
        
        for doc in source_documents:
            if isinstance(doc, dict):
                doc_title = doc.get("document_title", "").strip()
                if doc_title:
                    present_doc_types.add(doc_title)
        
        logger.debug(f"Found document types: {present_doc_types}")
        
        for required_doc in rules.required_documents:
            # Check for exact match or fuzzy match
            found = False
            for present_doc in present_doc_types:
                similarity = difflib.SequenceMatcher(None, required_doc.lower(), present_doc.lower()).ratio()
                if similarity >= 0.8:  # Allow some flexibility in document naming
                    found = True
                    break
            
            if not found:
                issues.append(ValidationIssue(
                    field="source_documents",
                    severity="error",
                    message=f"Required document type '{required_doc}' is missing",
                    extracted_value=list(present_doc_types),
                    expected_value=required_doc,
                    requires_review=False
                ))
                logger.warning(f"Document coverage check failed: missing '{required_doc}'")
        
        logger.debug(f"Document coverage check found {len(issues)} issues")
        return issues
    
    def _check_cross_field_consistency(
        self,
        summary: Dict[str, Any],
        rules: ValidationRuleSet
    ) -> List[ValidationIssue]:
        """
        Check that critical fields have consistent values across all citations.
        Uses fuzzy matching for fields in fuzzy_match_fields.
        """
        logger.debug("Running cross-field consistency check")
        issues = []
        
        citations = summary.get("citations", {})
        
        for field_path in rules.critical_fields:
            # Get the extracted value
            extracted_value = self._get_nested_value(summary, field_path)
            if extracted_value is None:
                continue  # Already caught by completeness check
            
            # Get all citations for this field
            field_citations = self._get_all_citations_for_field(citations, field_path)
            
            if len(field_citations) <= 1:
                continue  # No consistency check needed for single citation
            
            # Extract text snippets from citations
            citation_values = []
            for citation in field_citations:
                # Citation format: "Filename (Page X) - <Exact Text Snippet>"
                if " - " in citation:
                    snippet = citation.split(" - ", 1)[1].strip()
                    citation_values.append(snippet)
            
            # Check consistency
            is_fuzzy_field = field_path in rules.fuzzy_match_fields
            
            if not self._are_values_consistent(citation_values, is_fuzzy_field):
                severity = "warning" if is_fuzzy_field else "error"
                requires_review = is_fuzzy_field
                
                issues.append(ValidationIssue(
                    field=field_path,
                    severity=severity,
                    message=f"Inconsistent values found for '{field_path}' across documents: {citation_values}",
                    extracted_value=extracted_value,
                    expected_value="Consistent value across all documents",
                    source_citation="; ".join(field_citations),
                    requires_review=requires_review
                ))
                logger.warning(f"Consistency check failed for field: {field_path}")
        
        logger.debug(f"Cross-field consistency check found {len(issues)} issues")
        return issues
    
    def _check_proof_coverage(
        self,
        summary: Dict[str, Any],
        rules: ValidationRuleSet
    ) -> List[ValidationIssue]:
        """
        For array fields with proof requirements, verify each entity has corresponding proof.
        """
        logger.debug("Running proof coverage check")
        issues = []
        
        if not rules.array_proof_mappings:
            logger.debug("No array proof mappings defined, skipping proof coverage check")
            return issues
        
        source_documents = summary.get("source_documents", [])
        
        for array_path, proof_field in rules.array_proof_mappings.items():
            array_value = self._get_nested_value(summary, array_path)
            
            if not isinstance(array_value, list):
                continue
            
            # Check each entity in the array
            for idx, entity in enumerate(array_value):
                if not isinstance(entity, dict):
                    continue
                
                proof_value = entity.get(proof_field)
                
                if not proof_value:
                    issues.append(ValidationIssue(
                        field=f"{array_path}[{idx}].{proof_field}",
                        severity="warning",
                        message=f"Entity at {array_path}[{idx}] is missing proof field '{proof_field}'",
                        extracted_value=entity,
                        expected_value=f"Valid {proof_field}",
                        requires_review=True
                    ))
                    logger.warning(f"Proof coverage check failed for {array_path}[{idx}]")
        
        logger.debug(f"Proof coverage check found {len(issues)} issues")
        return issues

    def _check_evidence_requirements(
        self,
        summary: Dict[str, Any],
        rules: ValidationRuleSet
    ) -> List[ValidationIssue]:
        """
        Verify that fields are extracted from the correct supporting documents
        as defined in proof_requirements.
        """
        logger.debug("Running evidence requirements check")
        issues = []
        
        if not rules.proof_requirements:
            return issues
            
        citations = summary.get("citations", {})
        source_documents = summary.get("source_documents", [])
        
        # Build map for quick doc type lookup: (filename, page) -> doc_title
        doc_type_map = {}
        for doc in source_documents:
            filename = doc.get("filename")
            doc_title = doc.get("document_title")
            pages = doc.get("page_numbers", [])
            for p in pages:
                doc_type_map[(filename, p)] = doc_title

        for field_path, required_types in rules.proof_requirements.items():
            field_citations = self._get_all_citations_for_field(citations, field_path)
            
            if not field_citations:
                continue # Missing field handled by completeness check
            
            # Identify which document types actually proved this field
            found_doc_types = set()
            for citation in field_citations:
                # Citation format: "Filename (Page X) - Snippet"
                match = re.search(r"^(.*?) \(Page (\d+)\)", citation)
                if match:
                    fname, pnum = match.group(1), int(match.group(2))
                    dtype = doc_type_map.get((fname, pnum))
                    if dtype:
                        found_doc_types.add(dtype)
            
            # Check if all required types are satisfied
            for req_type in required_types:
                # Fuzzy matching for document types
                is_satisfied = any(
                    difflib.SequenceMatcher(None, req_type.lower(), found.lower()).ratio() >= 0.8
                    for found in found_doc_types
                )
                
                if not is_satisfied:
                    issues.append(ValidationIssue(
                        field=field_path,
                        severity="error",
                        message=f"Field '{field_path}' is missing mandatory proof from '{req_type}'",
                        extracted_value=None,
                        expected_value=f"Evidence in {req_type}",
                        requires_review=False
                    ))
                    logger.warning(f"Evidence check failed for '{field_path}': Missing '{req_type}'")

        return issues
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """
        Get a value from a nested dictionary using dot notation.
        Supports array indexing (e.g., "family_members[0].name")
        """
        parts = path.replace("[", ".").replace("]", "").split(".")
        current = obj
        
        for part in parts:
            if current is None:
                return None
            
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index] if index < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        
        return current
    
    def _get_all_citations_for_field(
        self,
        citations: Dict[str, str],
        field_path: str
    ) -> List[str]:
        """
        Get all citations that match the given field path.
        Handles both exact matches and array element matches.
        """
        matching_citations = []
        
        for citation_key, citation_value in citations.items():
            # Exact match
            if citation_key == field_path:
                if citation_value:
                    matching_citations.append(citation_value)
            # Array element match (e.g., "family_members[0].name" matches "family_members.*.name")
            elif self._is_array_field_match(citation_key, field_path):
                if citation_value:
                    matching_citations.append(citation_value)
        
        return matching_citations
    
    def _is_array_field_match(self, citation_key: str, field_path: str) -> bool:
        """
        Check if a citation key matches a field path pattern.
        E.g., "family_members[0].name" matches "family_members.name"
        """
        # Remove array indices from citation key
        normalized_citation = citation_key.replace("[", ".").replace("]", "")
        normalized_citation_parts = [p for p in normalized_citation.split(".") if not p.isdigit()]
        
        normalized_field = field_path.replace("[", ".").replace("]", "")
        normalized_field_parts = [p for p in normalized_field.split(".") if not p.isdigit()]
        
        return normalized_citation_parts == normalized_field_parts
    
    def _are_values_consistent(
        self,
        values: List[str],
        use_fuzzy: bool
    ) -> bool:
        """
        Check if a list of values are consistent.
        Uses exact matching or fuzzy matching based on use_fuzzy flag.
        """
        if len(values) <= 1:
            return True
        
        if use_fuzzy:
            # All values must be similar to the first value
            reference = values[0].lower().strip()
            for value in values[1:]:
                similarity = difflib.SequenceMatcher(None, reference, value.lower().strip()).ratio()
                if similarity < self.fuzzy_threshold:
                    logger.debug(f"Fuzzy match failed: '{reference}' vs '{value}' (similarity={similarity:.2f})")
                    return False
            return True
        else:
            # All values must be exactly the same (case-insensitive)
            reference = values[0].lower().strip()
            for value in values[1:]:
                if value.lower().strip() != reference:
                    logger.debug(f"Exact match failed: '{reference}' vs '{value}'")
                    return False
            return True
    
    def _calculate_approval_status(
        self,
        issues: List[ValidationIssue]
    ) -> Tuple[bool, float]:
        """
        Calculate auto-approval status and confidence score based on issues.
        
        Returns:
            Tuple of (auto_approved, confidence_score)
        """
        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        
        # Auto-approve only if no errors
        auto_approved = error_count == 0
        
        # Calculate confidence score
        # Start at 1.0, subtract 0.3 per error and 0.1 per warning
        confidence_score = 1.0 - (0.3 * error_count) - (0.1 * warning_count)
        confidence_score = max(0.0, min(1.0, confidence_score))  # Clamp to [0, 1]
        
        logger.debug(f"Approval calculation: errors={error_count}, warnings={warning_count}, "
                    f"auto_approved={auto_approved}, confidence={confidence_score:.2f}")
        
        return auto_approved, confidence_score
    
    def _generate_summary(
        self,
        issues: List[ValidationIssue],
        auto_approved: bool
    ) -> str:
        """
        Generate a natural language summary of the validation results.
        """
        if auto_approved and len(issues) == 0:
            return "All validation checks passed. Application is ready for approval."
        
        if auto_approved and len(issues) > 0:
            warning_count = sum(1 for i in issues if i.severity == "warning")
            return f"Application can be auto-approved with {warning_count} warning(s) that may require review."
        
        error_count = sum(1 for i in issues if i.severity == "error")
        error_fields = [i.field for i in issues if i.severity == "error"]
        
        if error_count == 1:
            return f"Application cannot be approved: {error_fields[0]} has validation errors."
        else:
            return f"Application cannot be approved: {error_count} validation errors found in fields: {', '.join(error_fields[:3])}{'...' if len(error_fields) > 3 else ''}."
