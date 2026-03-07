"""
Extraction Router - WITH PAGE RANGE SUPPORT
Location: src/strategies/router.py
"""

from typing import Optional, Tuple, List
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
from src.models.schemas import OriginType, ExtractedDocument, DocumentProfile
from src.utils.ocr_postprocess import fix_word_boundaries


class ExtractionRouter:
    """Extraction Router with page range support"""
    
    def __init__(self, config_path: str = "rubric/extraction_rules.yaml", max_budget_usd: float = 0.50):
        self.threshold_a = 0.85
        self.threshold_b = 0.75
        self.max_budget_usd = max_budget_usd
        
        config_file = Path(config_path)
        if config_file.exists() and YAML_AVAILABLE:
            try:
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                self.threshold_a = config.get('confidence', {}).get('strategy_a_threshold', 0.85)
                self.threshold_b = config.get('confidence', {}).get('strategy_b_threshold', 0.75)
                logger.info(f"Loaded config from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config: {e}. Using defaults.")
        
        self.strategy_a = FastTextExtractor()
        self.strategy_b = LayoutAwareExtractor()
        
        logger.info(f"ExtractionRouter initialized (thresholds: A={self.threshold_a}, B={self.threshold_b})")
    
    def extract(self, pdf_path: str, profile: DocumentProfile, page_range: Optional[List[int]] = None) -> Tuple[ExtractedDocument, str]:
        """Extract with page range support"""
        logger.info(f"Routing extraction for {pdf_path}")
        logger.info(f"Profile: {profile.origin_type} | {profile.layout_complexity}")
        logger.info(f"Page range: {page_range if page_range else 'ALL'}")
        
        if profile.origin_type == OriginType.NATIVE_DIGITAL:
            logger.info("Digital document: Starting from Strategy A")
            try:
                return self._try_strategy_a(pdf_path, profile, page_range)
            except Exception as e:
                logger.warning(f"Strategy A failed: {e}")
                return self._try_strategy_b(pdf_path, profile, page_range)
        else:
            logger.info("Scanned/form document: Starting from Strategy B")
            return self._try_strategy_b(pdf_path, profile, page_range)
    
    def _try_strategy_a(self, pdf_path: str, profile: DocumentProfile, page_range: Optional[List[int]] = None) -> Tuple[ExtractedDocument, str]:
        """Try Strategy A with page range"""
        logger.info("Trying Strategy A (Fast Text)")
        
        try:
            result = self.strategy_a.extract(pdf_path, page_range=page_range)
            
            if result.quality_score >= self.threshold_a:
                logger.success(f"Strategy A succeeded (quality: {result.quality_score:.2f})")
                return result, "strategy_a"
            
            return self._try_strategy_b(pdf_path, profile, page_range)
            
        except Exception as e:
            logger.error(f"Strategy A failed: {e}")
            return self._try_strategy_b(pdf_path, profile, page_range)
    
    def _try_strategy_b(self, pdf_path: str, profile: DocumentProfile, page_range: Optional[List[int]] = None) -> Tuple[ExtractedDocument, str]:
        """Try Strategy B WITH PAGE RANGE"""
        logger.info("Trying Strategy B (Layout-Aware)")
        
        try:
            # Pass page_range to strategy
            result = self.strategy_b.extract(pdf_path, page_range=page_range)
            
            if result.content:
                result.content = fix_word_boundaries(result.content)
            
            return result, "strategy_b"
            
        except Exception as e:
            logger.error(f"Strategy B failed: {e}")
            raise RuntimeError(f"Strategy B failed for {pdf_path}: {e}")
