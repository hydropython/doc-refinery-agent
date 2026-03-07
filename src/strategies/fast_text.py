"""
Strategy A: Fast Text Extraction (pdfplumber)
Location: src/strategies/fast_text.py

Uses pdfplumber for text and table extraction from native digital PDFs
"""

import pdfplumber
from pathlib import Path
from typing import List, Optional
from loguru import logger
from src.models.schemas import ExtractedDocument
from src.strategies.base import BaseExtractor


class FastTextExtractor(BaseExtractor):
    """Strategy A: Fast text extraction using pdfplumber"""
    
    def __init__(self, confidence_threshold: float = 0.85):
        super().__init__(
            strategy_name="strategy_a",
            cost_per_page=0.00,  # Free - local processing
            confidence_threshold=confidence_threshold
        )
        logger.info("FastTextExtractor initialized (pdfplumber)")
    
    def extract(self, pdf_path: str, page_range: Optional[List[int]] = None) -> ExtractedDocument:
        """
        Extract text from PDF using pdfplumber
        
        Args:
            pdf_path: Path to PDF file
            page_range: Optional list of pages to extract (e.g., [27, 28, 29])
        """
        logger.info(f"FastText extraction: {pdf_path}")
        if page_range:
            logger.info(f"Page range: {page_range}")
        
        all_text_parts = []
        page_markers = []
        tables_found = 0
        total_pages = 0
        pages_processed = 0
        
        with pdfplumber.open(pdf_path) as pdf:
            # FIX: Use len(pdf.pages) NOT len(pdf)
            total_pages = len(pdf.pages)
            
            # Support page range
            if page_range:
                pages_to_process = [p - 1 for p in page_range if p <= total_pages]
            else:
                pages_to_process = range(total_pages)
            
            pages_processed = len(pages_to_process)
            logger.info(f"Processing {pages_processed} pages")
            
            for page_num in pages_to_process:
                page = pdf.pages[page_num]  # FIX: Use pdf.pages[page_num]
                actual_page = page_num + 1
                
                # Extract text
                text = page.extract_text()
                if text and text.strip():
                    all_text_parts.append(text)
                    page_markers.append(actual_page)
                
                # Extract tables
                tables = page.extract_tables()
                if tables:
                    tables_found += len(tables)
                    for table in tables:
                        if table:
                            table_text = "\n".join([
                                " | ".join([str(cell) if cell else "" for cell in row])
                                for row in table if row
                            ])
                            if table_text.strip():
                                all_text_parts.append(table_text)
        
        # Combine results
        full_content = "\n\n".join(all_text_parts)
        total_chars = len(full_content)
        
        # Quality score
        quality_score = min(1.0, total_chars / 10000) if total_chars > 0 else 0.0
        
        logger.success(f"Extraction complete: {total_chars:,} chars, {tables_found} tables, quality: {quality_score:.2f}")
        
        return ExtractedDocument(
            doc_id=Path(pdf_path).stem,
            content=full_content,
            source_path=pdf_path,
            page_markers=page_markers,
            quality_score=quality_score,
            extraction_strategy="fast_text_pdfplumber",
            metadata={
                "pages_processed": pages_processed,
                "total_pages": total_pages,
                "tables_found": tables_found, "table_count": tables_found, "docling_tables": tables_found
            }
        )


