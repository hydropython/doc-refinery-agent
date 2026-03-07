"""
Extraction Agent - WITH PAGE RANGE SUPPORT
Location: src/agents/extractor.py
"""

from loguru import logger
from src.strategies.router import ExtractionRouter
from src.models.schemas import DocumentProfile, OriginType, ExtractedDocument
from typing import Tuple, List, Optional


class ExtractionAgent:
    """Extraction Agent with page range support"""
    
    def __init__(self, config_path: str = "rubric/extraction_rules.yaml"):
        self.router = ExtractionRouter(config_path=config_path)
        logger.info("ExtractionAgent initialized")
    
    def extract(self, pdf_path: str, profile: DocumentProfile, page_range: Optional[List[int]] = None) -> Tuple[ExtractedDocument, str]:
        """
        Extract content using router for strategy selection
        
        Args:
            pdf_path: Path to PDF file
            profile: DocumentProfile from triage
            page_range: List of page numbers to extract (1-indexed)
        
        Returns:
            Tuple of (ExtractedDocument, strategy_name)
        """
        logger.info(f"Extracting {pdf_path} with profile: {profile.origin_type}")
        logger.info(f"Page range: {page_range if page_range else 'ALL'}")
        
        # Use router for confidence-gated strategy selection WITH PAGE RANGE
        result, strategy = self.router.extract(pdf_path, profile, page_range)
        
        logger.info(f"Extraction complete via {strategy}")
        
        return result, strategy
    
    def get_cost_estimate(self, profile: DocumentProfile) -> float:
        """Get estimated cost for extraction"""
        return self.router.strategy_b.get_cost_estimate(profile.page_count)
