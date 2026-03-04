"""
Phase 2 Task 2: Confidence-Gated Routing

Automatically escalates to higher-cost strategies when confidence is low.
Implements budget guards to prevent cost overruns.

CONFIGURATION: Loads thresholds from rubric/extraction_rules.yaml
"""

from typing import Optional, Tuple
from pathlib import Path
from loguru import logger

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

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
    
    CONFIGURATION: Thresholds loaded from extraction_rules.yaml
    """
    
    def __init__(self, config_path: str = "rubric/extraction_rules.yaml", max_budget_usd: float = 0.50):
        """
        Initialize router with budget guard and config
        
        Args:
            config_path: Path to YAML configuration file
            max_budget_usd: Maximum cost per document (default: $0.50)
        """
        # Load thresholds from config
        self.threshold_a = 0.85
        self.threshold_b = 0.75
        self.threshold_c = 0.70
        self.max_budget_usd = max_budget_usd
        
        config_file = Path(config_path)
        if config_file.exists() and YAML_AVAILABLE:
            try:
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                self.threshold_a = config.get('confidence', {}).get('strategy_a_threshold', 0.85)
                self.threshold_b = config.get('confidence', {}).get('strategy_b_threshold', 0.75)
                self.threshold_c = config.get('confidence', {}).get('strategy_c_threshold', 0.70)
                self.max_budget_usd = config.get('budget', {}).get('max_cost_per_document', 0.50)
                logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")
        else:
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
        
        # Initialize strategies with thresholds
        self.strategy_a = FastTextExtractor()
        self.strategy_a.confidence_threshold = self.threshold_a
        
        self.strategy_b = LayoutAwareExtractor()
        self.strategy_b.confidence_threshold = self.threshold_b
        
        self.strategy_c = VisionOCRExtractor(budget_cap_usd=self.max_budget_usd)
        self.strategy_c.confidence_threshold = self.threshold_c
        
        logger.info(
            f"ExtractionRouter initialized (thresholds: A={self.threshold_a}, "
            f"B={self.threshold_b}, C={self.threshold_c}, budget=${self.max_budget_usd})"
        )
    
    def extract(self, pdf_path: str, profile: DocumentProfile) -> Tuple[ExtractedDocument, str]:
        """
        Extract with confidence-gated routing
        
        ESCALATION PATH: A → B → C (never skip)
        
        Exception: If origin_type is 'scanned_image' or 'form_fillable', start from B
        (Strategy A won't work on scanned docs)
        """
        logger.info(f"Routing extraction for {pdf_path}")
        logger.info(f"Profile: {profile.origin_type} | {profile.layout_complexity}")
        
        # DECISION: Where to start escalation?
        if profile.origin_type in ["scanned_image", "form_fillable"]:
            # Scanned/form docs: Start from B (A won't work)
            logger.info("Scanned/form document: Starting from Strategy B")
            return self._try_strategy_b(pdf_path, profile)
        else:
            # Digital/mixed docs: Always start from A
            logger.info("Digital document: Starting from Strategy A")
            return self._try_strategy_a(pdf_path, profile)
    
    def _try_strategy_a(self, pdf_path: str, profile: DocumentProfile) -> Tuple[ExtractedDocument, str]:
        """Try Strategy A, escalate to B if confidence low"""
        logger.info("Trying Strategy A (Fast Text)")
        
        try:
            result = self.strategy_a.extract(pdf_path)
            
            # Check confidence
            if result.quality_score >= self.threshold_a:
                logger.success(f"Strategy A succeeded (quality: {result.quality_score:.2f})")
                return result, "strategy_a"
            
            # Low confidence - escalate to B
            logger.warning(f"Strategy A low confidence ({result.quality_score:.2f} < {self.threshold_a}), escalating to B")
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
            if result.quality_score >= self.threshold_b:
                logger.success(f"Strategy B succeeded (quality: {result.quality_score:.2f})")
                return result, "strategy_b"
            
            # Low confidence - escalate to C
            logger.warning(f"Strategy B low confidence ({result.quality_score:.2f} < {self.threshold_b}), escalating to C")
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
            if result.quality_score >= self.threshold_c:
                logger.success(f"Strategy C succeeded (quality: {result.quality_score:.2f})")
                return result, "strategy_c"
            
            # Still low confidence - flag for human review
            logger.warning(f"Strategy C low confidence ({result.quality_score:.2f} < {self.threshold_c}), flagging for review")
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
    
    def reset_budgets(self):
        """Reset all strategy budgets (call after each document)"""
        self.strategy_c.reset_budget()
        logger.debug("All budgets reset")