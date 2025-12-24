import re
import difflib
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.verification.schema import (
    VerificationConfig, 
    VerificationReport, 
    VerificationIssue, 
    ValidationSummary,
    SchemaProjection,
    FieldEntity,
    FieldRelationship,
    KeyDetailDefinition, 
    ValidationRuleDefinition
)
from app.logging_config import get_logger

logger = get_logger(__name__)

class VerificationEngine:
    """
    The NEW core verification engine. 
    Strictly enforces Canonical Universal Extraction Response.
    """
    
    def verify(self, extraction_summary: Dict[str, Any], config: VerificationConfig) -> VerificationReport:
        # Detect Universal Extraction Format
        if "schema_projection" in extraction_summary:
            return self._verify_universal(extraction_summary, config)

        # Fallback LEGACY path (if input is old style)
        logger.warning(f"Legacy extraction summary detected for {config.application_type}. input structure mismatch.")
        
        # We return a valid empty report to satisfy the type system, but log the error.
        return VerificationReport(
            application_type=config.application_type,
            documents=[],
            field_entities=[],
            field_relationships=[],
            schema_projection=SchemaProjection(schema_name=config.application_type, ordered_fields=[], unmapped_fields=[]),
            validation_summary=ValidationSummary(total_schema_fields=0, validated_fields=0, errors=0, warnings=0, confidence_score=0.0),
            issues=[],
            metadata={"err": "Legacy input not supported", "original_input_keys": list(extraction_summary.keys())}
        )

    def _verify_universal(self, data: Dict[str, Any], config: VerificationConfig) -> VerificationReport:
        """
        Handles the Universal Extraction/Validation JSON structure (Strict).
        Computes final metrics and returns the Canonical Response.
        """
        # 1. Parse Schema Projection
        ordered_fields = data.get('schema_projection', {}).get('ordered_fields', [])
        
        # 2. Parse Issues & Metrics
        issues = []
        raw_issues = data.get('issues', [])
        error_count = 0
        warning_count = 0
        
        for i in raw_issues:
            sev = i.get('severity', 'error')
            if sev == 'error': error_count += 1
            if sev == 'warning': warning_count += 1
            
            issues.append(VerificationIssue(
                schema_field=i.get('schema_field', 'unknown'),
                severity=sev,
                message=i.get('message', ''),
                related_field_ids=i.get('related_field_ids', []),
                requires_review=i.get('requires_review', False)
            ))

        # 3. Compute Metrics
        total_fields = len(config.key_details)
        validated = len([f for f in ordered_fields if f.get('value') is not None])
        
        # Confidence Score: Base on % validated - penalty for errors
        base_score = (validated / total_fields) if total_fields > 0 else 0.0
        # If strict errors exist, confidence drops significantly
        confidence = max(0.0, min(1.0, base_score - (error_count * 0.15)))

        validation_summary = ValidationSummary(
            total_schema_fields=total_fields,
            validated_fields=validated,
            errors=error_count,
            warnings=warning_count,
            confidence_score=round(confidence, 2)
        )

        # 4. Return CANONICAL Response
        # Note: We reconstruct objects to ensure validation against Pydantic models
        return VerificationReport(
            application_type=config.application_type,
            documents=data.get('documents', []),
            field_entities=[FieldEntity(**f) for f in data.get('field_entities', [])],
            field_relationships=[FieldRelationship(**r) for r in data.get('field_relationships', [])],
            schema_projection=SchemaProjection(**data.get('schema_projection', {})),
            validation_summary=validation_summary,
            issues=issues,
            metadata=data.get('metadata', {})
        )
