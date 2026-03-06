#!/usr/bin/env python3
"""
Strategy B: Layout-Aware OCR (OFFLINE VERSION)

Uses RapidOCR for text extraction from scanned/mixed PDFs.
100% Local - No Network Required.
"""

from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
import fitz  # PyMuPDF
from rapidocr_onnxruntime import RapidOCR

from src.models.schemas import ExtractedDocument, BoundingBox


class LayoutAwareExtractor:
    """Extract text from scanned/mixed PDFs using RapidOCR (offline)"""
    
    def __init__(self):
        self.confidence_threshold = 0.75
        self.cost_per_page = 0.00
        self.ocr = RapidOCR()
        logger.info("LayoutAwareExtractor initialized (RapidOCR, offline)")
    
    def extract(self, pdf_path: str) -> ExtractedDocument:
        """Extract text from PDF using OCR"""
        logger.info(f"Extracting with RapidOCR: {pdf_path}")
        
        all_text_parts = []
        page_markers = []
        tables = []
        figures = []
        
        # Open PDF
        pdf = fitz.open(pdf_path)
        
        # FIXED: Use range(len(pdf)) instead of pdf.pages
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            actual_page = page_num + 1
            logger.debug(f"Processing page {actual_page}")
            
            # Convert page to image for OCR
            mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better OCR
            pix = page.get_pixmap(matrix=mat)
            
            # Save temp image
            img_path = Path(f".refinery/debug/ocr_page_{actual_page}.png")
            img_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(img_path))
            
            # Run OCR
            result, _ = self.ocr(str(img_path))
            
            if result:
                # Extract text from OCR results
                page_text = "\n".join([r[1] for r in result])
                
                if page_text.strip():
                    all_text_parts.append(page_text)
                    page_markers.append(actual_page)
                    
                    # Check for figure captions
                    for r in result:
                        text = r[1]
                        if 'Figure' in text or 'Fig.' in text:
                            figures.append({
                                'caption': text[:200],
                                'page': actual_page,
                                'bbox': r[0]
                            })
            
            # Clean up temp image
            try:
                img_path.unlink()
            except:
                pass
        
        pdf.close()
        
        # Combine all text
        content = "\n\n".join(all_text_parts)
        
        # Calculate quality score
        if content:
            space_ratio = content.count(' ') / max(len(content), 1)
            quality = min(space_ratio / 0.18, 1.0) * 0.5 + 0.3
            if len(content) > 100:
                quality = min(quality + 0.2, 1.0)
        else:
            quality = 0.1
        
        logger.info(f"OCR extracted {len(content)} chars from {len(page_markers)} pages")
        
        # Return ExtractedDocument
        return ExtractedDocument(
            doc_id=Path(pdf_path).stem,
            source_path=pdf_path,
            content=content,
            tables=tables,
            figures=figures,
            page_markers=page_markers,
            extraction_strategy="strategy_b",
            quality_score=quality
        )
    
    def get_cost_estimate(self, page_count: int) -> float:
        """Strategy B is free (local OCR)"""
        return 0.00
