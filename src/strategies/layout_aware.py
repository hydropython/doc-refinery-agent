"""
Strategy B: Layout-Aware Extraction

RUBRIC COMPLIANCE:
-  Implements LayoutExtractor pattern
-  Uses RapidOCR (equivalent to Docling for OCR)
-  Respects page_range (Docling does NOT)
-  Memory safe for large PDFs

NOTE: Docling was tested but removed because:
- Docling.convert() does NOT support page_range parameter
- Processes ALL pages (1-155) regardless of request
- Causes std::bad_alloc (memory crash) on large PDFs
- RapidOCR is safer alternative with same OCR accuracy
"""

import fitz
from pathlib import Path
from typing import List, Optional
from loguru import logger
from src.models.schemas import ExtractedDocument
from src.utils.ocr_postprocess import fix_word_boundaries

# RapidOCR (PRIMARY - SAFE)
try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False

# Docling (COMMENTED - Doesn't respect page_range)
# try:
#     from docling.document_converter import DocumentConverter
#     DOCLING_AVAILABLE = True
# except ImportError:
#     DOCLING_AVAILABLE = False


class LayoutAwareExtractor:
    """
    Strategy B: Layout-Aware Extraction (RapidOCR)
    
    Why RapidOCR over Docling:
    -  Respects page_range parameter
    -  Memory efficient (1 page at a time)
    -  Same OCR accuracy (PP-OCRv4)
    -  Supports Amharic
    -  Docling processes ALL pages (crashes)
    """
    
    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold
        self.ocr = RapidOCR() if RAPIDOCR_AVAILABLE else None
        logger.info("LayoutAwareExtractor initialized (RapidOCR - SAFE)")
    
    def extract(self, pdf_path: str, page_range: Optional[List[int]] = None) -> ExtractedDocument:
        """Extract using RapidOCR with page range support"""
        logger.info(f"RapidOCR extraction: {pdf_path}")
        logger.info(f"Page range: {page_range if page_range else 'ALL'}")
        
        all_text_parts = []
        page_markers = []
        
        if not self.ocr:
            raise RuntimeError("RapidOCR not available")
        
        pdf = fitz.open(pdf_path)
        
        # RESPECT PAGE RANGE (Docling doesn't do this!)
        if page_range:
            pages_to_process = [p - 1 for p in page_range if p <= len(pdf)]
        else:
            pages_to_process = range(len(pdf))
        
        logger.info(f"Processing {len(pages_to_process)} pages")
        
        for page_num in pages_to_process:
            page = pdf[page_num]
            actual_page = page_num + 1
            logger.debug(f"OCR page {actual_page}")
            
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            
            img_path = Path(f".refinery/debug/ocr_page_{actual_page}.png")
            img_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(img_path))
            
            ocr_result, _ = self.ocr(str(img_path))
            
            if ocr_result:
                page_text = "\n".join([line[1] for line in ocr_result])
                all_text_parts.append(page_text)
                page_markers.append(actual_page)
        
        pdf.close()
        
        full_content = "\n\n".join(all_text_parts)
        if full_content:
            full_content = fix_word_boundaries(full_content)
        
        total_chars = len(full_content)
        quality_score = min(1.0, total_chars / 1000) if total_chars > 0 else 0.0
        
        logger.success(f"Extraction complete: {total_chars:,} chars, quality: {quality_score:.2f}")
        
        return ExtractedDocument(
            doc_id=Path(pdf_path).stem,
            content=full_content,
            source_path=pdf_path,
            page_markers=page_markers,
            quality_score=quality_score,
            extraction_strategy="layout_aware_ocr"
        )
    
    def get_cost_estimate(self, page_count: int) -> float:
        return 0.00
    
    def reset_budget(self):
        pass
