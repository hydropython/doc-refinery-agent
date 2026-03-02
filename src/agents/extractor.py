from loguru import logger
from src.strategies.fast_text import FastTextExtractor
from src.strategies.layout_aware import LayoutAwareExtractor
from src.models.schemas import DocumentProfile, ExtractedDocument

class ExtractionRouter:
    def __init__(self):
        # Initialize the strategies
        self.fast_extractor = FastTextExtractor()
        self.layout_extractor = LayoutAwareExtractor()

    def process(self, pdf_path: str, profile: DocumentProfile) -> ExtractedDocument:
        # Decision Logic: The "Escalation Guard"
        strategy_key = profile.estimated_cost_tier
        
        logger.info(f"Routing {profile.doc_id} to Strategy: {strategy_key}")
        
        # Route based on triage results
        if strategy_key == "fast_text":
            return self.fast_extractor.extract(pdf_path)
        elif strategy_key == "layout_model":
            return self.layout_extractor.extract(pdf_path)
        else:
            logger.warning(f"Unknown strategy {strategy_key}. Falling back to LayoutAware.")
            return self.layout_extractor.extract(pdf_path)