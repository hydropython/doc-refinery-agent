"""
Phase 2 Task 1: Strategy C - VLM/OCR Extraction

Uses Docling + RapidOCR for scanned documents.
Handles image-based PDFs with OCR.

BUDGET GUARD: Tracks token spend and enforces configurable budget cap.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from src.strategies.base import BaseExtractor
from src.models.schemas import ExtractedDocument, LogicalDocumentUnit


class BudgetExceededError(Exception):
    """Raised when extraction would exceed budget cap"""
    pass


class VisionOCRExtractor(BaseExtractor):
    """
    Strategy C: VLM/OCR Extraction
    
    Best for:
    - Scanned documents
    - Image-based PDFs
    - Low text density documents
    - Form-fillable PDFs
    
    BUDGET GUARD:
    - Tracks running cost per document
    - Enforces configurable budget cap
    - Raises BudgetExceededError if cap exceeded
    """
    
    def __init__(self, budget_cap_usd: float = 0.50):
        super().__init__(
            strategy_name="strategy_c",
            cost_per_page=0.002,
            confidence_threshold=0.70
        )
        self.budget_cap_usd = budget_cap_usd
        self.running_cost = 0.0
        self.ocr = None
        self.docling = None
        logger.info(f"VisionOCRExtractor initialized (budget cap: ${budget_cap_usd})")
    
    def _initialize(self):
        """Lazy-load OCR and Docling"""
        if self.ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self.ocr = RapidOCR()
                logger.info("RapidOCR initialized successfully")
            except ImportError:
                logger.warning("RapidOCR not installed. Using Docling fallback.")
                self.ocr = None
        
        if self.docling is None:
            try:
                from docling.document_converter import DocumentConverter
                self.docling = DocumentConverter()
                logger.info("Docling initialized successfully")
            except ImportError:
                logger.error("Docling not installed. Strategy C cannot function.")
                raise RuntimeError("Docling required for Strategy C")
    
    def _check_budget(self, page_count: int) -> bool:
        """
        Check if extraction would exceed budget
        
        Args:
            page_count: Number of pages to extract
            
        Returns:
            True if within budget, False if exceeded
        """
        estimated_cost = page_count * self.cost_per_page
        total_projected = self.running_cost + estimated_cost
        
        if total_projected > self.budget_cap_usd:
            logger.warning(
                f"Budget exceeded: ${total_projected:.2f} > ${self.budget_cap_usd} "
                f"(running: ${self.running_cost:.2f}, estimated: ${estimated_cost:.2f})"
            )
            return False
        
        return True
    
    def _update_running_cost(self, page_count: int):
        """Update running cost after extraction"""
        cost = page_count * self.cost_per_page
        self.running_cost += cost
        logger.debug(f"Updated running cost: ${self.running_cost:.2f}")
    
    def extract(self, pdf_path: str) -> ExtractedDocument:
        """
        Extract document using OCR + Docling
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ExtractedDocument with OCR'd content
            
        Raises:
            BudgetExceededError: If extraction would exceed budget cap
        """
        self._initialize()
        logger.info(f"Strategy C: Extracting {pdf_path}")
        
        # Check budget before extraction
        try:
            import fitz  # PyMuPDF for page count
            with fitz.open(pdf_path) as pdf:
                page_count = len(pdf)
            
            if not self._check_budget(page_count):
                raise BudgetExceededError(
                    f"Extraction would exceed budget cap of ${self.budget_cap_usd}"
                )
        except ImportError:
            logger.warning("PyMuPDF not installed. Skipping budget check.")
        
        try:
            # Convert PDF with Docling (OCR mode)
            result = self.docling.convert(pdf_path)
            
            # Extract text content
            content = result.document.export_to_text()
            
            # If low text, use RapidOCR as fallback
            if len(content) < 100 and self.ocr is not None:
                logger.warning("Docling produced low text. Using RapidOCR fallback.")
                content = self._ocr_fallback(pdf_path)
            
            # Extract tables
            tables = self._extract_tables(result)
            
            # Extract figures
            figures = self._extract_figures(result)
            
            # Create page markers
            page_markers = self._create_page_markers(result)
            
            # Calculate quality score
            quality_score = self._calculate_quality(content, tables, figures)
            
            # Update running cost
            self._update_running_cost(len(page_markers))
            
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
        """
        Fallback to RapidOCR if Docling fails
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            OCR'd text content
        """
        import fitz  # PyMuPDF
        
        text_parts = []
        with fitz.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf):
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # OCR the image
                result, _ = self.ocr(img_data)
                if result:
                    page_text = " ".join([line[1] for line in result])
                    text_parts.append(page_text)
                    logger.debug(f"Page {page_num + 1}: OCR'd {len(page_text)} chars")
        
        return "\n".join(text_parts)
    
    def _extract_tables(self, result) -> List[Dict[str, Any]]:
        """Extract tables with structure"""
        tables = []
        
        try:
            # Extract tables from Docling result
            if hasattr(result, 'document') and hasattr(result.document, 'tables'):
                for table in result.document.tables:
                    table_data = {
                        "rows": [],
                        "bbox": table.bbox if hasattr(table, 'bbox') else None,
                        "page_refs": [1]  # Would track actual pages
                    }
                    
                    # Extract rows
                    if hasattr(table, 'data'):
                        for row in table.data:
                            table_data["rows"].append([str(cell) for cell in row])
                    
                    tables.append(table_data)
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
        
        return tables
    
    def _extract_figures(self, result) -> List[Dict[str, Any]]:
        """Extract figures with captions"""
        figures = []
        
        try:
            # Extract figures from Docling result
            if hasattr(result, 'document') and hasattr(result.document, 'figures'):
                for figure in result.document.figures:
                    figure_data = {
                        "description": "",
                        "caption": getattr(figure, 'caption', ''),
                        "bbox": figure.bbox if hasattr(figure, 'bbox') else None,
                        "page_refs": [1]  # Would track actual pages
                    }
                    figures.append(figure_data)
        except Exception as e:
            logger.warning(f"Figure extraction failed: {e}")
        
        return figures
    
    def _create_page_markers(self, result) -> List[int]:
        """Create page boundary markers"""
        markers = []
        
        try:
            # Get page count from Docling result
            if hasattr(result, 'document') and hasattr(result.document, 'pages'):
                for i, page in enumerate(result.document.pages):
                    markers.append(i + 1)
        except Exception as e:
            logger.warning(f"Page marker creation failed: {e}")
            markers = [1]  # Default to single page
        
        return markers
    
    def _calculate_quality(self, content: str, tables: List, figures: List) -> float:
        """
        Calculate extraction quality score
        
        Args:
            content: Extracted text content
            tables: List of extracted tables
            figures: List of extracted figures
            
        Returns:
            Quality score (0.0-1.0)
        """
        if not content:
            return 0.0
        
        # Base score from content length
        base_score = min(len(content) / 10000, 1.0)
        
        # OCR confidence bonus
        ocr_bonus = 0.2  # Assume good OCR if we got content
        
        # Structure bonus for tables/figures
        structure_bonus = min((len(tables) + len(figures)) / 10, 0.3)
        
        quality = min(base_score + ocr_bonus + structure_bonus, 1.0)
        
        logger.debug(f"Quality score: {quality:.2f} (base: {base_score:.2f}, ocr: {ocr_bonus}, structure: {structure_bonus:.2f})")
        
        return quality
    
    def reset_budget(self):
        """Reset running cost (call after each document)"""
        self.running_cost = 0.0
        logger.debug("Budget reset to $0.00")
    
    def get_running_cost(self) -> float:
        """Get current running cost"""
        return self.running_cost