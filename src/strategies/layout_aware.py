"""
Strategy B: Layout-Aware Extraction (RapidOCR - SAFE)
WITH IMAGE & TABLE COUNTING PER PAGE
"""

import fitz
from pathlib import Path
from typing import List, Optional, Dict, Any
from loguru import logger
from src.models.schemas import ExtractedDocument
from src.utils.ocr_postprocess import fix_word_boundaries

try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False


class LayoutAwareExtractor:
    """Strategy B: RapidOCR with image/table counting"""
    
    def __init__(self, confidence_threshold: float = 0.75):
        self.confidence_threshold = confidence_threshold
        self.ocr = RapidOCR() if RAPIDOCR_AVAILABLE else None
        logger.info("LayoutAwareExtractor initialized (RapidOCR - SAFE)")
    
    def extract(self, pdf_path: str, page_range: Optional[List[int]] = None) -> ExtractedDocument:
        """Extract with image/table counting per page"""
        logger.info(f"RapidOCR extraction: {pdf_path}")
        logger.info(f"Page range: {page_range if page_range else 'ALL'}")
        
        all_text_parts = []
        page_markers = []
        page_stats = []  # NEW: Track stats per page
        
        if not self.ocr:
            raise RuntimeError("RapidOCR not available")
        
        pdf = fitz.open(pdf_path)
        
        # Support page range
        if page_range:
            pages_to_process = [p - 1 for p in page_range if p <= len(pdf)]
        else:
            pages_to_process = range(len(pdf))
        
        logger.info(f"Processing {len(pages_to_process)} pages")
        
        for page_num in pages_to_process:
            page = pdf[page_num]
            actual_page = page_num + 1
            logger.debug(f"OCR page {actual_page}")
            
            # COUNT IMAGES
            images = page.get_images(full=True)
            image_count = len(images)
            
            # COUNT TABLES
            tables = page.find_tables()
            table_count = len(tables.tables)
            
            # Convert page to image for OCR
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            
            img_path = Path(f".refinery/debug/ocr_page_{actual_page}.png")
            img_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(str(img_path))
            
            # Run OCR
            ocr_result, _ = self.ocr(str(img_path))
            
            if ocr_result:
                page_text = "\n".join([line[1] for line in ocr_result])
                all_text_parts.append(page_text)
                page_markers.append(actual_page)
                
                # Track page stats
                page_stats.append({
                    "page": actual_page,
                    "images": image_count,
                    "tables": table_count,
                    "chars": len(page_text)
                })
        
        pdf.close()
        
        # Combine results
        full_content = "\n\n".join(all_text_parts)
        if full_content:
            full_content = fix_word_boundaries(full_content)
        
        total_chars = len(full_content)
        quality_score = min(1.0, total_chars / 1000) if total_chars > 0 else 0.0
        
        # Summary stats
        total_images = sum(p["images"] for p in page_stats)
        total_tables = sum(p["tables"] for p in page_stats)
        
        logger.success(f"Extraction complete: {total_chars:,} chars, quality: {quality_score:.2f}")
        logger.info(f"Pages: {len(page_stats)}, Images: {total_images}, Tables: {total_tables}")
        
        # Log per-page stats
        for stat in page_stats:
            logger.info(f"  Page {stat['page']}: {stat['images']} images, {stat['tables']} tables, {stat['chars']:,} chars")
        
        return ExtractedDocument(
            doc_id=Path(pdf_path).stem,
            content=full_content,
            source_path=pdf_path,
            page_markers=page_markers,
            quality_score=quality_score,
            extraction_strategy="layout_aware_ocr",
            metadata={
                "page_stats": page_stats,
                "total_images": total_images,
                "total_tables": total_tables
            }
        )
    
    def get_cost_estimate(self, page_count: int) -> float:
        return 0.00
    
    def reset_budget(self):
        pass
