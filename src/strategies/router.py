"""
Extraction Router - Uses extraction_rules.yaml
"""

import yaml
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger
from src.models.schemas import DocumentProfile, ExtractedDocument


class ExtractionRouter:
    def __init__(self, config_path: str = "rubric/extraction_rules.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._init_strategies()
    
    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}
    
    def _init_strategies(self):
        self.strategy_a = None
        self.strategy_b = None
        
        try:
            from src.strategies.fast_text import FastTextExtractor
            self.strategy_a = FastTextExtractor()
            logger.debug("Strategy A initialized")
        except Exception as e:
            logger.warning(f"Strategy A init failed: {e}")
        
        try:
            from src.strategies.layout_aware import LayoutAwareExtractor
            self.strategy_b = LayoutAwareExtractor()
            logger.debug("Strategy B initialized")
        except Exception as e:
            logger.warning(f"Strategy B init failed: {e}")
    
    def extract(self, pdf_path: str, profile: DocumentProfile, 
                page_range: Optional[List[int]] = None,
                force_strategy: str = None) -> Tuple[ExtractedDocument, str]:
        
        logger.info(f"Routing: {profile.origin_type.value} | {profile.layout_complexity.value}")
        logger.info(f"Tables: {profile.table_count}, Images: {profile.images_found}")
        
        # Get thresholds from config
        conf = self.config.get('confidence', {})
        threshold_b = conf.get('strategy_b_threshold', 0.75)
        
        # TABLE-HEAVY  Strategy B (from config: trigger_table_heavy: true)
        if profile.layout_complexity.value == 'table_heavy' or profile.table_count >= 3:
            logger.info("Table-heavy (config rule)  Using Strategy B")
            if self.strategy_b:
                result = self.strategy_b.extract(pdf_path, page_range)
                return result, "strategy_b"
        
        # SCANNED  Strategy B (from config: trigger_scanned: true)
        if profile.origin_type.value == 'scanned_image':
            logger.info("Scanned (config rule)  Using Strategy B")
            if self.strategy_b:
                result = self.strategy_b.extract(pdf_path, page_range)
                return result, "strategy_b"
        
        # IMAGE-HEAVY  Strategy B
        if profile.images_found >= 5:
            logger.info("Image-heavy  Using Strategy B")
            if self.strategy_b:
                result = self.strategy_b.extract(pdf_path, page_range)
                return result, "strategy_b"
        
        # DEFAULT  Strategy A
        if self.strategy_a:
            logger.info("Default  Using Strategy A")
            result = self.strategy_a.extract(pdf_path, page_range)
            return result, "strategy_a"
        
        # FALLBACK  Strategy B
        if self.strategy_b:
            logger.info("Fallback  Using Strategy B")
            result = self.strategy_b.extract(pdf_path, page_range)
            return result, "strategy_b"
        
        raise RuntimeError("All strategies failed")
