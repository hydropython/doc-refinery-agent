#!/usr/bin/env python3
"""
OCR Quality Checker
Calculates quality metrics from extracted text based on Phase 0 benchmarks
"""

import re
from typing import Dict, Tuple


class OCRQualityChecker:
    """Calculate OCR quality metrics based on Phase 0 empirical findings"""
    
    # Error patterns from Phase 0 benchmark (65 errors across 10 files)
    DIGIT_ERROR_PATTERNS = [
        (r'\b3o\b', '30'),           # "3oJune" → "30June"
        (r'\b2o\b', '20'),           # "2o23" → "2023"
        (r'\b1o\b', '10'),           # "1o%" → "10%"
        (r'(?<!\d)O(?=\d)', '0'),    # "O123" → "0123"
        (r'(?<=\d)o(?!\d)', '0'),    # "123o" → "1230"
    ]
    
    SPACING_ERROR_PATTERNS = [
        (r'([A-Z])([A-Z][a-z])', r'\1 \2'),    # "BankOf" → "Bank Of"
        (r'([a-z])([A-Z])', r'\1 \2'),         # "incomeFor" → "income For"
        (r'(\d)([A-Z])', r'\1 \2'),            # "2023June" → "2023 June"
        (r'([A-Z])(\d)', r'\1 \2'),            # "June2023" → "June 2023"
        (r'(June|July|Aug|Sept|Oct|Nov|Dec)(\d)', r'\1 \2'),
        (r'(Birr|USD|EUR)(\d)', r'\1 \2'),
        (r'(Report|Statement|Financial)(\d)', r'\1 \2'),
    ]
    
    def __init__(self):
        self.digit_errors = 0
        self.spacing_errors = 0
    
    def count_errors(self, text: str) -> Tuple[int, int]:
        """Count digit and spacing errors in text"""
        digit_errors = 0
        spacing_errors = 0
        
        for pattern, _ in self.DIGIT_ERROR_PATTERNS:
            digit_errors += len(re.findall(pattern, text))
        
        for pattern, _ in self.SPACING_ERROR_PATTERNS:
            spacing_errors += len(re.findall(pattern, text))
        
        return digit_errors, spacing_errors
    
    def calculate_quality_score(self, text: str, digit_errors: int, spacing_errors: int) -> float:
        """Calculate overall quality score (0-1)"""
        total_chars = len(text)
        if total_chars == 0:
            return 0.0
        
        total_errors = digit_errors + spacing_errors
        error_rate = total_errors / total_chars
        
        # Quality score: 1.0 = perfect, decreases with errors
        # Phase 0 benchmark: 0.95 average for scanned docs
        quality_score = max(0.0, 1.0 - (error_rate * 10))
        return round(quality_score, 4)
    
    def analyze(self, text: str) -> Dict:
        """Full quality analysis"""
        digit_errors, spacing_errors = self.count_errors(text)
        total_chars = len(text)
        
        quality_score = self.calculate_quality_score(text, digit_errors, spacing_errors)
        
        return {
            'total_chars': total_chars,
            'digit_errors': digit_errors,
            'spacing_errors': spacing_errors,
            'total_errors': digit_errors + spacing_errors,
            'error_rate': round((digit_errors + spacing_errors) / max(total_chars, 1), 6),
            'quality_score': quality_score,
            'status': 'PASS' if quality_score >= 0.75 else 'FAIL'
        }


def calculate_ocr_quality(text: str) -> Dict:
    """
    Main entry point for OCR quality calculation
    
    Args:
        text: Extracted text from Docling/VLM
        
    Returns:
        Dict with quality metrics (quality_score, digit_errors, spacing_errors, etc.)
    """
    checker = OCRQualityChecker()
    return checker.analyze(text)


def normalize_ocr_text(text: str) -> Tuple[str, Dict]:
    """
    Apply normalization rules to fix common OCR errors
    
    Returns:
        Tuple of (corrected_text, metrics)
    """
    checker = OCRQualityChecker()
    corrected = text
    
    # Apply digit corrections
    for pattern, replacement in checker.DIGIT_ERROR_PATTERNS:
        corrected = re.sub(pattern, replacement, corrected)
    
    # Apply spacing corrections
    for pattern, replacement in checker.SPACING_ERROR_PATTERNS:
        corrected = re.sub(pattern, replacement, corrected)
    
    # Calculate metrics
    metrics = checker.analyze(text)
    metrics['corrected_chars'] = len(corrected)
    
    return corrected, metrics