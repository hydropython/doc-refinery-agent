#!/usr/bin/env python3
"""
Strategy A: Fast Text Extraction

For native digital PDFs with embedded text.
"""

from pathlib import Path
import pdfplumber
from src.models.schemas import ExtractedDocument


class FastTextExtractor:
    """Extract text from digital PDFs using pdfplumber"""
    
    def __init__(self):
        self.confidence_threshold = 0.85
        self.cost_per_page = 0.00
    
    def extract(self, pdf_path: str) -> ExtractedDocument:
        """Extract text from digital PDF"""
        
        full_text = []
        page_markers = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                full_text.append(text)
                page_markers.append(i + 1)
        
        content = "\n\n".join(full_text)
        
        # Calculate quality score based on text density
        space_ratio = content.count(' ') / max(len(content), 1) if content else 0
        quality = min(space_ratio / 0.18, 1.0) * 0.5 + 0.5
        
        # RETURN PROPER ExtractedDocument WITH CORRECT FIELD NAMES
        return ExtractedDocument(
            doc_id=Path(pdf_path).stem,
            source_path=pdf_path,
            content=content,
            tables=[],
            figures=[],
            page_markers=page_markers,
            extraction_strategy="strategy_a",
            quality_score=quality
        )
    
    def get_cost_estimate(self, page_count: int) -> float:
        """Strategy A is free (local text extraction)"""
        return 0.00
