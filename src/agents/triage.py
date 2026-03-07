"""
Triage Agent - Fixed Table/Image Detection
"""

import fitz
import pdfplumber
from pathlib import Path
from typing import List, Optional
from loguru import logger
from src.models.schemas import DocumentProfile, OriginType, LayoutComplexity


class TriageAgent:
    def __init__(self, config_path: str = "rubric/extraction_rules.yaml"):
        self.config_path = Path(config_path)
    
    def analyze(self, pdf_path: str) -> DocumentProfile:
        """Analyze document and return profile"""
        
        pdf = fitz.open(pdf_path)
        page_count = len(pdf)
        
        text_chars = 0
        image_count = 0
        table_count = 0
        has_font_meta = False
        embedded_fonts = 0
        
        # Use pdfplumber for better table detection
        try:
            with pdfplumber.open(pdf_path) as pdf_plumber:
                for page in pdf_plumber.pages[:11]:
                    tables = page.extract_tables()
                    if tables:
                        table_count += len(tables)
        except:
            pass
        
        # Use fitz for text and images
        for page_num in range(min(11, page_count)):
            page = pdf[page_num]
            
            text = page.get_text()
            text_chars += len(text)
            
            # Check fonts
            fonts = page.get_fonts()
            if fonts:
                has_font_meta = True
                embedded_fonts += len(fonts)
            
            # Count images
            images = page.get_images()
            image_count += len(images)
        
        pdf.close()
        
        # Calculate density
        page_area = 595 * 842
        char_density = text_chars / (page_area * page_count) if page_count > 0 else 0
        image_ratio = image_count / page_count if page_count > 0 else 0
        
        # Determine origin type
        if char_density < 0.01 or image_ratio > 0.5:
            origin_type = OriginType.SCANNED_IMAGE
        elif char_density > 0.10 and image_ratio < 0.30:
            origin_type = OriginType.NATIVE_DIGITAL
        else:
            origin_type = OriginType.MIXED
        
        # Determine layout complexity - FIXED: table_count >= 3
        if table_count >= 3:
            layout_complexity = LayoutComplexity.TABLE_HEAVY
        elif image_count >= 5:
            layout_complexity = LayoutComplexity.IMAGE_HEAVY
        elif char_density < 0.05:
            layout_complexity = LayoutComplexity.MODERATE
        else:
            layout_complexity = LayoutComplexity.SIMPLE
        
        # Recommend strategy - FIXED: table_heavy  strategy_b
        if layout_complexity == LayoutComplexity.TABLE_HEAVY:
            recommended_strategy = "strategy_b"
        elif origin_type == OriginType.SCANNED_IMAGE:
            recommended_strategy = "strategy_b"
        elif layout_complexity == LayoutComplexity.IMAGE_HEAVY:
            recommended_strategy = "strategy_b"
        else:
            recommended_strategy = "strategy_a"
        
        confidence = 0.95 if has_font_meta else 0.85
        cost_tier = "free_local"
        
        return DocumentProfile(
            origin_type=origin_type,
            layout_complexity=layout_complexity,
            recommended_strategy=recommended_strategy,
            confidence_score=confidence,
            text_chars=text_chars,
            images_found=image_count,
            table_count=table_count,
            page_count=page_count,
            char_density=char_density,
            has_font_meta=has_font_meta,
            embedded_fonts=embedded_fonts,
            estimated_cost_tier=cost_tier
        )
