"""
Document Classifier Module
Automatically identifies document/certificate types based on content analysis
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    """Result of document classification"""
    certificate_type: str
    confidence: float
    keywords_found: List[str]
    reason: str

class DocumentClassifier:
    """Classifies documents based on content to determine certificate type"""
    
    def __init__(self):
        self.classification_patterns = self._create_classification_patterns()
    
    def _create_classification_patterns(self) -> Dict[str, Dict]:
        """Create patterns for different certificate types"""
        return {
            'integrated': {
                'keywords': [
                    'integrated', 'community', 'nativ', 'birth', 'caste', 'religion',
                    'nativity', 'place of birth', 'certificate for', 'kula dhruveekarana', 'ధృవీకరణ'
                ],
                'patterns': [
                    r'integrated.*certificate',
                    r'caste.*community.*certificate',
                    r'birth.*certificate',
                    r'nativ.*certificate',
                    r'kula.*dhruveekarana',  # Telugu for caste certificate
                ],
                'required_keywords': ['certificate'],
            },
            'income': {
                'keywords': [
                    'income', 'annual income', 'salary', 'wages', 'business income',
                    'agricultural income', 'total income', 'assessing officer', 'revenue',
                    'income certificate', 'annual income certificate', 'salary slip'
                ],
                'patterns': [
                    r'income.*certificate',
                    r'annual.*income',
                    r'total.*income',
                    r'salary.*certificate',
                ],
                'required_keywords': ['income'],
            },
            'obc': {
                'keywords': [
                    'obc', 'other backward class', 'backward class', 'class other',
                    'obc certificate', 'backward caste', 'other backward classes'
                ],
                'patterns': [
                    r'obc.*certificate',
                    r'other.*backward.*class',
                    r'backward.*class.*certificate',
                ],
                'required_keywords': ['obc', 'backward'],
            },
            'ews': {
                'keywords': [
                    'ews', 'economically weaker', 'economically weaker section',
                    'weaker section', 'annual income', 'economically backward',
                    'ews certificate', 'poor', 'income limit'
                ],
                'patterns': [
                    r'ews.*certificate',
                    r'economically.*weaker.*section',
                    r'weaker.*section.*certificate',
                ],
                'required_keywords': ['ews', 'economically', 'weaker'],
            },
            'family_member': {
                'keywords': [
                    'family member', 'head of family', 'family certificate', 'h.o.f',
                    'family composition', 'household', 'deceased', 'death certificate',
                    'family tree', 'family record', 'house of family', 'kutumbam'
                ],
                'patterns': [
                    r'family.*member.*certificate',
                    r'family.*composition',
                    r'deceased.*family',
                    r'kutumbam.*certificate',  # Telugu for family
                ],
                'required_keywords': ['family', 'member', 'deceased'],
            }
        }
    
    def classify_document(self, extracted_text: str) -> ClassificationResult:
        """
        Classify a document based on its extracted text content
        
        Args:
            extracted_text: Text content of the document
            
        Returns:
            ClassificationResult with the most likely certificate type
        """
        text_lower = extracted_text.lower()
        
        scores = {}
        matched_keywords = {}
        
        # Calculate score for each certificate type
        for cert_type, patterns in self.classification_patterns.items():
            score = 0
            found_keywords = []
            
            # Check for keyword matches
            for keyword in patterns['keywords']:
                if keyword in text_lower:
                    score += 1
                    found_keywords.append(keyword)
            
            # Check for pattern matches (more weight)
            for pattern in patterns['patterns']:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score += 2  # Higher weight for regex patterns
                    found_keywords.extend([pattern])
            
            # Check for required keywords
            has_required = False
            for req_kw in patterns['required_keywords']:
                if req_kw in text_lower:
                    has_required = True
                    break
            
            if has_required:
                scores[cert_type] = score
                matched_keywords[cert_type] = found_keywords
            else:
                scores[cert_type] = 0  # Don't classify if required keywords missing
        
        # Find the type with the highest score
        if scores:
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]
            
            # Calculate confidence (normalize score by total possible keywords)
            total_keywords = sum(len(patterns['keywords']) + len(patterns['patterns']) 
                                for patterns in self.classification_patterns.values())
            confidence = min(1.0, best_score / (total_keywords * 0.5)) if total_keywords > 0 else 0.0
            
            return ClassificationResult(
                certificate_type=best_type,
                confidence=confidence,
                keywords_found=matched_keywords.get(best_type, []),
                reason=f"Best match based on {best_score} keyword/pattern matches"
            )
        else:
            # Default to income if no strong matches
            return ClassificationResult(
                certificate_type='income',
                confidence=0.1,
                keywords_found=[],
                reason="No strong matches found, defaulting to income certificate"
            )
    
    def classify_from_file_content(self, file_path: Path, extracted_text: str) -> ClassificationResult:
        """
        Classify document combining file path hints with content analysis
        
        Args:
            file_path: Path to the document file
            extracted_text: Extracted text content
            
        Returns:
            ClassificationResult with certificate type
        """
        # First, try content-based classification
        content_result = self.classify_document(extracted_text)
        
        # Enhance with filename analysis
        file_name_lower = file_path.name.lower()
        
        # Boost confidence if filename contains relevant keywords
        file_boost = 0
        for cert_type, patterns in self.classification_patterns.items():
            for keyword in patterns['keywords']:
                if keyword in file_name_lower:
                    if content_result.certificate_type == cert_type:
                        file_boost += 0.1
                    break
        
        # Adjust confidence based on filename hints
        adjusted_confidence = min(1.0, content_result.confidence + file_boost)
        
        return ClassificationResult(
            certificate_type=content_result.certificate_type,
            confidence=adjusted_confidence,
            keywords_found=content_result.keywords_found,
            reason=f"Content analysis: {content_result.reason}, File name boost: {file_boost:.1f}"
        )

    def get_certificate_suggestions(self, extracted_text: str, top_n: int = 3) -> List[ClassificationResult]:
        """
        Get top N suggestions for certificate type
        
        Args:
            extracted_text: Text content of document
            top_n: Number of top suggestions to return
            
        Returns:
            List of top N classification results
        """
        text_lower = extracted_text.lower()
        
        scores = {}
        
        for cert_type, patterns in self.classification_patterns.items():
            score = 0
            found_keywords = []
            
            # Check for keyword matches
            for keyword in patterns['keywords']:
                if keyword in text_lower:
                    score += 1
                    found_keywords.append(keyword)
            
            # Check for pattern matches
            for pattern in patterns['patterns']:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    score += 2
                    found_keywords.extend([pattern])
            
            # Check for required keywords
            has_required = False
            for req_kw in patterns['required_keywords']:
                if req_kw in text_lower:
                    has_required = True
                    break
            
            if has_required:
                scores[cert_type] = (score, found_keywords)
            else:
                scores[cert_type] = (0, [])
        
        # Sort by score and return top N
        sorted_scores = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
        results = []
        
        for cert_type, (score, keywords) in sorted_scores[:top_n]:
            if score > 0:
                total_keywords = sum(len(patterns['keywords']) + len(patterns['patterns']) 
                                   for patterns in self.classification_patterns.values())
                confidence = min(1.0, score / (total_keywords * 0.5)) if total_keywords > 0 else 0.0
                
                results.append(ClassificationResult(
                    certificate_type=cert_type,
                    confidence=confidence,
                    keywords_found=keywords,
                    reason=f"Score: {score}"
                ))
        
        return results