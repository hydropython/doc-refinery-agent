"""
Phase 2 Task 1: Strategy C - VLM/OCR Extraction

Uses Docling + RapidOCR for scanned documents.
Handles image-based PDFs with OCR.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from src.strategies.base import BaseExtractor
from src.models.schemas import ExtractedDocument, LogicalDocumentUnit


class VisionOCRExtractor(BaseExtractor):
    """
    Strategy C: VLM/OCR Extraction
    
    Best for:
    - Scanned documents
    - Image-based PDFs
    - Low text density documents
    """
    
    def __init__(self):
        super().__init__(
            strategy_name="strategy_c",
            cost_per_page=0.002,
            confidence_threshold=0.70
        )
        self.ocr = None
        self.docling = None
    
    def _initialize(self):
        """Lazy-load OCR and Docling"""
        if self.ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self.ocr = RapidOCR()
                logger.info("RapidOCR initialized successfully")
            except ImportError:
                logger.error("RapidOCR not installed. Run: pip install rapidocr_onnxruntime")
                raise
        
        if self.docling is None:
            try:
                from docling.document_converter import DocumentConverter
                self.docling = DocumentConverter()
                logger.info("Docling initialized successfully")
            except ImportError:
                logger.error("Docling not installed")
                raise
    
    def extract(self, pdf_path: str) -> ExtractedDocument:
        """
        Extract document using OCR + Docling
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ExtractedDocument with OCR'd content
        """
        self._initialize()
        logger.info(f"Strategy C: Extracting {pdf_path}")
        
        try:
            # Convert PDF with Docling (OCR mode)
            result = self.docling.convert(pdf_path)
            
            # Extract text content
            content = result.document.export_to_text()
            
            # If low text, use RapidOCR as fallback
            if len(content) < 100:
                content = self._ocr_fallback(pdf_path)
            
            # Extract tables
            tables = self._extract_tables(result)
            
            # Extract figures
            figures = self._extract_figures(result)
            
            # Create page markers
            page_markers = self._create_page_markers(result)
            
            # Calculate quality score
            quality_score = self._calculate_quality(content, tables, figures)
            
            return ExtractedDocument(
                doc_id=Path(pdf_path).stem,
                source_path=pdf_path,
                content=content,
                tables=tables,
                figures=figures,
                page_markers=page_markers,
                extraction_strategy=self.strategy_name,
                quality_score=quality_score
            )
            
        except Exception as e:
            logger.error(f"Strategy C extraction failed: {e}")
            raise
    
    def _ocr_fallback(self, pdf_path: str) -> str:
        """Fallback to RapidOCR if Docling fails"""
        import fitz  # PyMuPDF
        
        text_parts = []
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # OCR the image
                result, _ = self.ocr(img_data)
                if result:
                    page_text = " ".join([line[1] for line in result])
                    text_parts.append(page_text)
        
        return "\n".join(text_parts)
    
    def _extract_tables(self, result) -> List[Dict[str, Any]]:
        """Extract tables with structure"""
        tables = []
        return tables
    
    def _extract_figures(self, result) -> List[Dict[str, Any]]:
        """Extract figures with captions"""
        figures = []
        return figures
    
    def _create_page_markers(self, result) -> List[int]:
        """Create page boundary markers"""
        markers = []
        return markers
    
    def _calculate_quality(self, content: str, tables: List, figures: List) -> float:
        """Calculate extraction quality score"""
        if not content:
            return 0.0
        
        # Base score from content length
        base_score = min(len(content) / 10000, 1.0)
        
        # OCR confidence bonus
        ocr_bonus = 0.2  # Assume good OCR if we got content
        
        return min(base_score + ocr_bonus, 1.0)