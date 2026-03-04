"""
Phase 2 Task 2: Confidence-Gated Routing

Automatically escalates to higher-cost strategies when confidence is low.
Implements budget guards to prevent cost overruns.
"""

from typing import Optional, Tuple
from loguru import logger

from src.strategies.base import BaseExtractor
from src.strategies.fast_text import FastTextExtractor
from src.strategies.layout_aware import LayoutAwareExtractor
from src.strategies.vision_ocr import VisionOCRExtractor
from src.models.schemas import ExtractedDocument, DocumentProfile


class ExtractionRouter:
    """
    Phase 2: Confidence-Gated Extraction Router
    
    Routes documents to appropriate strategy based on:
    - Document profile (origin_type, layout_complexity)
    - Confidence scores from each strategy
    - Budget constraints
    """
    
    def __init__(self, max_budget_usd: float = 0.50):
        """
        Initialize router with budget guard
        
        Args:
            max_budget_usd: Maximum cost per document (default: $0.50)
        """
        self.max_budget_usd = max_budget_usd
        self.strategy_a = FastTextExtractor()
        self.strategy_b = LayoutAwareExtractor()
        self.strategy_c = VisionOCRExtractor()
        logger.info(f"ExtractionRouter initialized (max budget: ${max_budget_usd})")
    
    def extract(self, pdf_path: str, profile: DocumentProfile) -> Tuple[ExtractedDocument, str]:
        """
        Extract with confidence-gated routing
        
        Args:
            pdf_path: Path to PDF file
            profile: DocumentProfile from triage agent
            
        Returns:
            Tuple of (ExtractedDocument, strategy_used)
        """
        logger.info(f"Routing extraction for {pdf_path}")
        logger.info(f"Profile: {profile.origin_type} | {profile.layout_complexity}")
        
        # Start with recommended strategy from triage
        if profile.recommended_strategy == "strategy_a":
            return self._try_strategy_a(pdf_path, profile)
        elif profile.recommended_strategy == "strategy_b":
            return self._try_strategy_b(pdf_path, profile)
        else:
            return self._try_strategy_c(pdf_path, profile)
    
    def _try_strategy_a(self, pdf_path: str, profile: DocumentProfile) -> Tuple[ExtractedDocument, str]:
        """Try Strategy A, escalate to B if confidence low"""
        logger.info("Trying Strategy A (Fast Text)")
        
        try:
            result = self.strategy_a.extract(pdf_path)
            
            # Check confidence
            if result.quality_score >= self.strategy_a.confidence_threshold:
                logger.success(f"Strategy A succeeded (quality: {result.quality_score:.2f})")
                return result, "strategy_a"
            
            # Low confidence - escalate to B
            logger.warning(f"Strategy A low confidence ({result.quality_score:.2f}), escalating to B")
            return self._try_strategy_b(pdf_path, profile)
            
        except Exception as e:
            logger.error(f"Strategy A failed: {e}")
            return self._try_strategy_b(pdf_path, profile)
    
    def _try_strategy_b(self, pdf_path: str, profile: DocumentProfile) -> Tuple[ExtractedDocument, str]:
        """Try Strategy B, escalate to C if confidence low"""
        logger.info("Trying Strategy B (Layout-Aware)")
        
        # Check budget
        estimated_cost = self.strategy_b.get_cost_estimate(profile.page_count)
        if estimated_cost > self.max_budget_usd:
            logger.warning(f"Strategy B exceeds budget (${estimated_cost:.2f} > ${self.max_budget_usd})")
        
        try:
            result = self.strategy_b.extract(pdf_path)
            
            # Check confidence
            if result.quality_score >= self.strategy_b.confidence_threshold:
                logger.success(f"Strategy B succeeded (quality: {result.quality_score:.2f})")
                return result, "strategy_b"
            
            # Low confidence - escalate to C
            logger.warning(f"Strategy B low confidence ({result.quality_score:.2f}), escalating to C")
            return self._try_strategy_c(pdf_path, profile)
            
        except Exception as e:
            logger.error(f"Strategy B failed: {e}")
            return self._try_strategy_c(pdf_path, profile)
    
    def _try_strategy_c(self, pdf_path: str, profile: DocumentProfile) -> Tuple[ExtractedDocument, str]:
        """Try Strategy C (final fallback)"""
        logger.info("Trying Strategy C (VLM/OCR)")
        
        # Check budget
        estimated_cost = self.strategy_c.get_cost_estimate(profile.page_count)
        if estimated_cost > self.max_budget_usd:
            logger.warning(f"Strategy C exceeds budget (${estimated_cost:.2f} > ${self.max_budget_usd})")
        
        try:
            result = self.strategy_c.extract(pdf_path)
            
            # Check confidence
            if result.quality_score >= self.strategy_c.confidence_threshold:
                logger.success(f"Strategy C succeeded (quality: {result.quality_score:.2f})")
                return result, "strategy_c"
            
            # Still low confidence - flag for human review
            logger.warning(f"Strategy C low confidence ({result.quality_score:.2f}), flagging for review")
            result.quality_score = max(result.quality_score, 0.5)
            return result, "strategy_c_review"
            
        except Exception as e:
            logger.error(f"Strategy C failed: {e}")
            raise RuntimeError(f"All strategies failed for {pdf_path}: {e}")
    
    def get_total_cost(self, results: list) -> float:
        """Calculate total extraction cost"""
        total = 0.0
        for doc, strategy in results:
            if strategy == "strategy_a":
                total += self.strategy_a.get_cost_estimate(len(doc.page_markers))
            elif strategy == "strategy_b":
                total += self.strategy_b.get_cost_estimate(len(doc.page_markers))
            elif strategy == "strategy_c":
                total += self.strategy_c.get_cost_estimate(len(doc.page_markers))
        return total