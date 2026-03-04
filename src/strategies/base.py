"""
Phase 2: Base Extractor Class

Abstract base class for all extraction strategies.
Defines the interface that all strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from loguru import logger

from src.models.schemas import ExtractedDocument


class BaseExtractor(ABC):
    """
    Abstract base class for extraction strategies
    
    All extraction strategies (A, B, C) must inherit from this class
    and implement the extract() method.
    """
    
    def __init__(
        self,
        strategy_name: str,
        cost_per_page: float,
        confidence_threshold: float
    ):
        """
        Initialize base extractor
        
        Args:
            strategy_name: Name of the strategy (strategy_a, strategy_b, strategy_c)
            cost_per_page: Cost in USD per page
            confidence_threshold: Minimum confidence score (0.0-1.0)
        """
        self.strategy_name = strategy_name
        self.cost_per_page = cost_per_page
        self.confidence_threshold = confidence_threshold
        logger.debug(f"BaseExtractor initialized: {strategy_name}")
    
    @abstractmethod
    def extract(self, pdf_path: str) -> ExtractedDocument:
        """
        Extract content from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ExtractedDocument with full content and structure
        """
        pass
    
    def get_cost_estimate(self, page_count: int) -> float:
        """
        Estimate extraction cost
        
        Args:
            page_count: Number of pages in document
            
        Returns:
            Estimated cost in USD
        """
        return page_count * self.cost_per_page
    
    def meets_confidence_threshold(self, confidence: float) -> bool:
        """
        Check if confidence meets threshold
        
        Args:
            confidence: Confidence score (0.0-1.0)
            
        Returns:
            True if confidence >= threshold
        """
        return confidence >= self.confidence_threshold


class ExtractionResult:
    """
    Simple container for extraction results
    
    Used internally by strategies before creating ExtractedDocument
    """
    
    def __init__(
        self,
        content: str,
        tables: List[Dict[str, Any]] = None,
        figures: List[Dict[str, Any]] = None,
        page_markers: List[int] = None,
        quality_score: float = 0.0
    ):
        self.content = content
        self.tables = tables or []
        self.figures = figures or []
        self.page_markers = page_markers or []
        self.quality_score = quality_score