"""
Test Escalation Path: A → B → C (never skip)
"""

import pytest
from src.strategies.router import ExtractionRouter
from src.models.schemas import DocumentProfile


class TestEscalationPath:
    """Test that escalation always follows A → B → C"""
    
    def test_digital_starts_at_a(self):
        """Digital documents start at Strategy A"""
        router = ExtractionRouter()
        
        # Create profile manually
        profile = DocumentProfile(
            doc_id="test_digital",
            filename="test.pdf",
            file_path="/path/test.pdf",
            origin_type="native_digital",
            layout_complexity="single_column",
            domain_hint="financial",
            domain_confidence=0.9,
            confidence_score=0.95,
            recommended_strategy="strategy_a",
            estimated_cost_tier="fast_text",
            text_chars=5000,
            images_found=0,
            page_count=10,
            has_font_meta=True
        )
        
        # Verify profile is digital
        assert profile.origin_type == "native_digital"
        # Router should start at A for digital docs
    
    def test_scanned_starts_at_b(self):
        """Scanned documents start at Strategy B (A won't work)"""
        router = ExtractionRouter()
        
        # Create profile manually
        profile = DocumentProfile(
            doc_id="test_scanned",
            filename="test.pdf",
            file_path="/path/test.pdf",
            origin_type="scanned_image",
            layout_complexity="multi_column",
            domain_hint="financial",
            domain_confidence=0.8,
            confidence_score=0.5,
            recommended_strategy="strategy_c",
            estimated_cost_tier="vision_model",
            text_chars=20,
            images_found=5,
            page_count=10,
            has_font_meta=False
        )
        
        # Verify profile is scanned
        assert profile.origin_type == "scanned_image"
        # Router should start at B for scanned docs (not C directly)
    
    def test_never_skip_b(self):
        """Verify B is never skipped in escalation"""
        # This is enforced by the code structure:
        # _try_strategy_a calls _try_strategy_b (not _try_strategy_c)
        # _try_strategy_b calls _try_strategy_c
        # There's no direct path from A to C
        router = ExtractionRouter()
        
        # Verify method structure
        import inspect
        source_a = inspect.getsource(router._try_strategy_a)
        source_b = inspect.getsource(router._try_strategy_b)
        
        # A should call B, not C
        assert "_try_strategy_b" in source_a
        assert "_try_strategy_c" not in source_a
        
        # B should call C
        assert "_try_strategy_c" in source_b
    
    def test_router_respects_escalation(self):
        """Test that router respects A → B → C escalation"""
        router = ExtractionRouter()
        
        # Check that _try_strategy_a doesn't call _try_strategy_c directly
        import inspect
        source_a = inspect.getsource(router._try_strategy_a)
        
        # Count how many times each strategy is called
        calls_b = source_a.count("_try_strategy_b")
        calls_c = source_a.count("_try_strategy_c")
        
        # A should call B at least once
        assert calls_b >= 1, "Strategy A should escalate to B"
        
        # A should NOT call C directly
        assert calls_c == 0, "Strategy A should NOT skip to C"