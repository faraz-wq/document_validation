"""
Metrics and Evaluation Module
Provides comprehensive evaluation metrics for document validation workflow
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import re

logger = logging.getLogger(__name__)


@dataclass
class FieldMetrics:
    """Metrics for individual field extraction"""
    field_name: str
    true_positive: int = 0  # Correctly extracted
    false_positive: int = 0  # Extracted but wrong value
    false_negative: int = 0  # Not extracted but should be
    exact_matches: int = 0  # Exact string match
    partial_matches: int = 0  # Fuzzy match
    total_documents: int = 0

    @property
    def precision(self) -> float:
        """Precision = TP / (TP + FP)"""
        if self.true_positive + self.false_positive == 0:
            return 0.0
        return self.true_positive / (self.true_positive + self.false_positive)

    @property
    def recall(self) -> float:
        """Recall = TP / (TP + FN)"""
        if self.true_positive + self.false_negative == 0:
            return 0.0
        return self.true_positive / (self.true_positive + self.false_negative)

    @property
    def f1_score(self) -> float:
        """F1 = 2 * (Precision * Recall) / (Precision + Recall)"""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def accuracy(self) -> float:
        """Exact match accuracy"""
        if self.total_documents == 0:
            return 0.0
        return self.exact_matches / self.total_documents


@dataclass
class DocumentMetrics:
    """Metrics for a single document"""
    document_id: str
    processing_time: float
    total_fields: int
    extracted_fields: int
    correct_fields: int
    missing_fields: int
    incorrect_fields: int
    character_error_rate: Optional[float] = None
    word_error_rate: Optional[float] = None
    # Page-level tracking for PDFs
    page_count: Optional[int] = None
    is_multi_page: bool = False
    potential_multi_doc: bool = False
    # Warnings
    has_warnings: bool = False
    warning_messages: List[str] = None

    def __post_init__(self):
        """Initialize mutable defaults"""
        if self.warning_messages is None:
            self.warning_messages = []

    @property
    def extraction_rate(self) -> float:
        """Percentage of fields extracted"""
        if self.total_fields == 0:
            return 0.0
        return self.extracted_fields / self.total_fields

    @property
    def field_accuracy(self) -> float:
        """Percentage of correct fields"""
        if self.extracted_fields == 0:
            return 0.0
        return self.correct_fields / self.extracted_fields

    @property
    def fields_per_page(self) -> Optional[float]:
        """Average fields extracted per page (for PDFs)"""
        if not self.page_count or self.page_count == 0:
            return None
        return self.extracted_fields / self.page_count


@dataclass
class SummaryMetrics:
    """Metrics for Stage 2 summary generation"""
    summary_id: str
    total_required_fields: int
    fields_in_summary: int
    correct_values: int
    incorrect_values: int
    missing_values: int
    source_attribution_correct: int
    source_attribution_total: int
    cross_document_conflicts: int
    format_compliance: bool

    @property
    def completeness(self) -> float:
        """Percentage of required fields in summary"""
        if self.total_required_fields == 0:
            return 0.0
        return self.fields_in_summary / self.total_required_fields

    @property
    def value_accuracy(self) -> float:
        """Percentage of correct values"""
        if self.fields_in_summary == 0:
            return 0.0
        return self.correct_values / self.fields_in_summary

    @property
    def source_accuracy(self) -> float:
        """Percentage of correct source attributions"""
        if self.source_attribution_total == 0:
            return 0.0
        return self.source_attribution_correct / self.source_attribution_total


class MetricsCalculator:
    """Calculate various metrics for document validation"""

    @staticmethod
    def calculate_edit_distance(str1: str, str2: str) -> int:
        """
        Calculate Levenshtein edit distance between two strings

        Args:
            str1: First string
            str2: Second string

        Returns:
            Edit distance
        """
        m, n = len(str1), len(str2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str1[i - 1] == str2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1]
                else:
                    dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])

        return dp[m][n]

    @staticmethod
    def calculate_cer(ground_truth: str, predicted: str) -> float:
        """
        Calculate Character Error Rate

        Args:
            ground_truth: Ground truth text
            predicted: Predicted text

        Returns:
            CER value
        """
        if len(ground_truth) == 0:
            return 1.0 if len(predicted) > 0 else 0.0

        distance = MetricsCalculator.calculate_edit_distance(ground_truth, predicted)
        return distance / len(ground_truth)

    @staticmethod
    def calculate_wer(ground_truth: str, predicted: str) -> float:
        """
        Calculate Word Error Rate

        Args:
            ground_truth: Ground truth text
            predicted: Predicted text

        Returns:
            WER value
        """
        gt_words = ground_truth.split()
        pred_words = predicted.split()

        if len(gt_words) == 0:
            return 1.0 if len(pred_words) > 0 else 0.0

        distance = MetricsCalculator.calculate_edit_distance(
            ' '.join(gt_words), ' '.join(pred_words)
        )
        return distance / len(gt_words)

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for comparison

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        return text

    @staticmethod
    def fuzzy_match(str1: str, str2: str, threshold: float = 0.8) -> bool:
        """
        Check if two strings are similar enough

        Args:
            str1: First string
            str2: Second string
            threshold: Similarity threshold (0-1)

        Returns:
            True if similar enough
        """
        norm1 = MetricsCalculator.normalize_text(str1)
        norm2 = MetricsCalculator.normalize_text(str2)

        if len(norm1) == 0 and len(norm2) == 0:
            return True

        distance = MetricsCalculator.calculate_edit_distance(norm1, norm2)
        max_len = max(len(norm1), len(norm2))

        similarity = 1 - (distance / max_len) if max_len > 0 else 0
        return similarity >= threshold


class DocumentEvaluator:
    """Evaluate document extraction against ground truth"""

    def __init__(self, ground_truth_path: Optional[Path] = None):
        """
        Initialize evaluator

        Args:
            ground_truth_path: Path to ground truth annotations
        """
        self.ground_truth = {}
        if ground_truth_path and ground_truth_path.exists():
            self.load_ground_truth(ground_truth_path)

    def load_ground_truth(self, path: Path) -> None:
        """
        Load ground truth annotations

        Args:
            path: Path to JSON file with ground truth
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Support both single document and list of documents
        if isinstance(data, list):
            for doc in data:
                self.ground_truth[doc['document_id']] = doc
        else:
            self.ground_truth[data['document_id']] = data

        logger.info(f"Loaded ground truth for {len(self.ground_truth)} documents")

    def parse_extraction(self, extraction_text: str) -> Dict[str, str]:
        """
        Parse Stage 1 extraction text into field dictionary

        Args:
            extraction_text: Extracted text with key-value pairs

        Returns:
            Dictionary of field name to value
        """
        fields = {}
        lines = extraction_text.split('\n')

        current_key = None
        current_value = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line contains a colon (key-value separator)
            if ':' in line:
                # Save previous field if exists
                if current_key:
                    fields[current_key] = ' '.join(current_value).strip()

                # Parse new field
                parts = line.split(':', 1)
                current_key = parts[0].strip()
                current_value = [parts[1].strip()] if len(parts) > 1 else []
            else:
                # Continuation of previous value
                if current_key:
                    current_value.append(line)

        # Save last field
        if current_key:
            fields[current_key] = ' '.join(current_value).strip()

        return fields

    def evaluate_document(
        self,
        document_id: str,
        extraction_text: str,
        processing_time: float
    ) -> DocumentMetrics:
        """
        Evaluate a single document extraction

        Args:
            document_id: Document identifier
            extraction_text: Extracted text from Stage 1
            processing_time: Time taken to process

        Returns:
            DocumentMetrics object
        """
        if document_id not in self.ground_truth:
            logger.warning(f"No ground truth for document: {document_id}")
            return None

        gt = self.ground_truth[document_id]
        gt_fields = gt.get('ground_truth_fields', {})

        extracted_fields = self.parse_extraction(extraction_text)

        # Calculate metrics
        total_fields = len(gt_fields)
        extracted_count = len(extracted_fields)
        correct_fields = 0
        incorrect_fields = 0
        missing_fields = 0

        for field_name, gt_value in gt_fields.items():
            if field_name in extracted_fields:
                extracted_value = extracted_fields[field_name]
                if MetricsCalculator.fuzzy_match(gt_value, extracted_value):
                    correct_fields += 1
                else:
                    incorrect_fields += 1
            else:
                missing_fields += 1

        # Calculate CER and WER on full text
        gt_text = ' '.join(gt_fields.values())
        extracted_text_clean = ' '.join(extracted_fields.values())
        cer = MetricsCalculator.calculate_cer(gt_text, extracted_text_clean)
        wer = MetricsCalculator.calculate_wer(gt_text, extracted_text_clean)

        return DocumentMetrics(
            document_id=document_id,
            processing_time=processing_time,
            total_fields=total_fields,
            extracted_fields=extracted_count,
            correct_fields=correct_fields,
            missing_fields=missing_fields,
            incorrect_fields=incorrect_fields,
            character_error_rate=cer,
            word_error_rate=wer
        )

    def evaluate_summary(
        self,
        summary_table: str,
        expected_summary: Dict[str, Dict],
        summary_id: str
    ) -> SummaryMetrics:
        """
        Evaluate Stage 2 summary generation

        Args:
            summary_table: Generated summary markdown table
            expected_summary: Expected field values and sources
            summary_id: Summary identifier

        Returns:
            SummaryMetrics object
        """
        # Parse markdown table
        parsed_summary = self._parse_summary_table(summary_table)

        total_required = len(expected_summary)
        fields_in_summary = len(parsed_summary)
        correct_values = 0
        incorrect_values = 0
        missing_values = 0
        source_correct = 0
        source_total = 0

        for field_name, expected in expected_summary.items():
            if field_name in parsed_summary:
                actual = parsed_summary[field_name]

                # Check value accuracy
                if MetricsCalculator.fuzzy_match(expected['value'], actual['value']):
                    correct_values += 1
                else:
                    incorrect_values += 1

                # Check source attribution
                source_total += 1
                expected_sources = set(expected['source_documents'])
                actual_sources = set(actual['source_documents'])
                if expected_sources == actual_sources:
                    source_correct += 1
            else:
                missing_values += 1

        # Check format compliance (has proper table structure)
        format_compliance = '|' in summary_table and '---' in summary_table

        return SummaryMetrics(
            summary_id=summary_id,
            total_required_fields=total_required,
            fields_in_summary=fields_in_summary,
            correct_values=correct_values,
            incorrect_values=incorrect_values,
            missing_values=missing_values,
            source_attribution_correct=source_correct,
            source_attribution_total=source_total,
            cross_document_conflicts=0,  # Would need conflict detection logic
            format_compliance=format_compliance
        )

    def _parse_summary_table(self, table: str) -> Dict[str, Dict]:
        """Parse markdown table into structured data"""
        parsed = {}
        lines = table.split('\n')

        for line in lines:
            if '|' not in line or '---' in line:
                continue

            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:  # | Field | Value | Source |
                field = parts[1]
                value = parts[2]
                sources = [s.strip() for s in parts[3].split(',')]

                parsed[field] = {
                    'value': value,
                    'source_documents': sources
                }

        return parsed


class MetricsReporter:
    """Generate metrics reports"""

    @staticmethod
    def generate_report(
        document_metrics: List[DocumentMetrics],
        summary_metrics: Optional[SummaryMetrics] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        Generate comprehensive metrics report

        Args:
            document_metrics: List of document metrics
            summary_metrics: Optional summary metrics
            output_path: Optional path to save report

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("DOCUMENT VALIDATION METRICS REPORT".center(80))
        lines.append("=" * 80)
        lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Document-level metrics
        lines.append("-" * 80)
        lines.append("STAGE 1: DOCUMENT EXTRACTION METRICS")
        lines.append("-" * 80)

        if document_metrics:
            avg_extraction = sum(m.extraction_rate for m in document_metrics) / len(document_metrics)
            avg_accuracy = sum(m.field_accuracy for m in document_metrics) / len(document_metrics)
            avg_cer = sum(m.character_error_rate for m in document_metrics if m.character_error_rate) / len(document_metrics)
            avg_wer = sum(m.word_error_rate for m in document_metrics if m.word_error_rate) / len(document_metrics)
            avg_time = sum(m.processing_time for m in document_metrics) / len(document_metrics)

            lines.append(f"Total Documents: {len(document_metrics)}")
            lines.append(f"Average Extraction Rate: {avg_extraction:.2%}")
            lines.append(f"Average Field Accuracy: {avg_accuracy:.2%}")
            lines.append(f"Average CER: {avg_cer:.4f}")
            lines.append(f"Average WER: {avg_wer:.4f}")
            lines.append(f"Average Processing Time: {avg_time:.2f}s")

        # Summary metrics
        if summary_metrics:
            lines.append("\n" + "-" * 80)
            lines.append("STAGE 2: SUMMARY GENERATION METRICS")
            lines.append("-" * 80)
            lines.append(f"Completeness: {summary_metrics.completeness:.2%}")
            lines.append(f"Value Accuracy: {summary_metrics.value_accuracy:.2%}")
            lines.append(f"Source Attribution Accuracy: {summary_metrics.source_accuracy:.2%}")
            lines.append(f"Format Compliance: {'Yes' if summary_metrics.format_compliance else 'No'}")

        report = "\n".join(lines)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to: {output_path}")

        return report
