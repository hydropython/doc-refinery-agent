"""
Phase 1 Task 5: Unit Tests for Triage Agent

Tests cover:
- DocumentProfile model validation
- origin_type detection (scanned vs. digital vs. mixed)
- layout_complexity detection
- domain_hint classification
- Confidence scoring
"""

import pytest
from src.models.schemas import DocumentProfile, create_test_profile
from src.agents.triage import TriageAgent
from src.agents.domain_classifier import DomainClassifier, KeywordClassifier


class TestDocumentProfile:
    """Test DocumentProfile Pydantic model"""
    
    def test_profile_creation(self):
        """Test DocumentProfile can be created with all fields"""
        profile = DocumentProfile(
            doc_id="test_doc",
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
        assert profile.doc_id == "test_doc"
        assert profile.origin_type == "native_digital"
        assert profile.confidence_score == 0.95
    
    def test_profile_validation_origin(self):
        """Test origin_type validation"""
        # Scanned document
        scanned = create_test_profile(
            origin_type="scanned_image",
            text_chars=20,
            images_found=5
        )
        assert scanned.validate_origin_type() == True
        
        # Digital document
        digital = create_test_profile(
            origin_type="native_digital",
            text_chars=5000,
            images_found=0
        )
        assert digital.validate_origin_type() == True
    
    def test_profile_validation_layout(self):
        """Test layout_complexity validation"""
        profile = DocumentProfile(
            doc_id="test",
            filename="test.pdf",
            file_path="/path/test.pdf",
            origin_type="native_digital",
            layout_complexity="table_heavy",
            domain_hint="financial",
            domain_confidence=0.8,
            confidence_score=0.8,
            recommended_strategy="strategy_b",
            estimated_cost_tier="layout_model",
            table_count=5,
            column_count=1
        )
        assert profile.validate_layout_complexity() == True
    
    def test_get_strategy_name(self):
        """Test strategy name mapping"""
        profile = create_test_profile()
        assert "Strategy" in profile.get_strategy_name()


class TestTriageAgent:
    """Test Triage Agent classification logic"""
    
    @pytest.fixture
    def triage_agent(self):
        return TriageAgent()
    
    def test_scanned_detection(self, triage_agent):
        """Test scanned document detection (text_chars < 50)"""
        signals = {
            "text_chars": 20,
            "vector_chars": 20,
            "images_found": 5,
            "page_count": 1,
            "page_area": 10000,
            "char_density": 0.002,
            "image_area_ratio": 0.6,
            "has_font_meta": False,
            "column_count": 1,
            "table_count": 0,
            "figure_count": 0,
            "table_bboxes": [],
            "figure_bboxes": [],
            "font_names": [],
            "embedded_fonts": 0
        }
        origin_type = triage_agent._detect_origin_type(signals)
        assert origin_type == "scanned_image"
    
    def test_digital_detection(self, triage_agent):
        """Test digital document detection (text_chars > 1000)"""
        signals = {
            "text_chars": 5000,
            "vector_chars": 5000,
            "images_found": 0,
            "page_count": 1,
            "page_area": 10000,
            "char_density": 0.5,
            "image_area_ratio": 0.0,
            "has_font_meta": True,
            "column_count": 1,
            "table_count": 0,
            "figure_count": 0,
            "table_bboxes": [],
            "figure_bboxes": [],
            "font_names": [],
            "embedded_fonts": 0
        }
        origin_type = triage_agent._detect_origin_type(signals)
        assert origin_type == "native_digital"
    
    def test_table_heavy_detection(self, triage_agent):
        """Test table-heavy document detection (tables > 2)"""
        signals = {
            "table_count": 5,
            "column_count": 1,
            "figure_count": 0
        }
        layout = triage_agent._detect_layout_complexity(signals)
        assert layout == "table_heavy"
    
    def test_multi_column_detection(self, triage_agent):
        """Test multi-column detection"""
        signals = {
            "table_count": 0,
            "column_count": 2,
            "figure_count": 0
        }
        layout = triage_agent._detect_layout_complexity(signals)
        assert layout == "multi_column"
    
    def test_confidence_scoring_range(self, triage_agent):
        """Test confidence score is between 0.0 and 1.0"""
        signals = {
            "text_chars": 5000,
            "char_density": 0.5,
            "image_area_ratio": 0.0,
            "has_font_meta": True,
            "table_count": 2
        }
        confidence = triage_agent._calculate_confidence(signals, "native_digital")
        assert 0.0 <= confidence <= 1.0
    
    def test_strategy_recommendation(self, triage_agent):
        """Test strategy recommendation logic"""
        # Scanned -> Strategy C
        strategy = triage_agent._recommend_strategy("scanned_image", "single_column")
        assert strategy == "strategy_c"
        
        # Table-heavy -> Strategy B
        strategy = triage_agent._recommend_strategy("native_digital", "table_heavy")
        assert strategy == "strategy_b"
        
        # Digital + single column -> Strategy A
        strategy = triage_agent._recommend_strategy("native_digital", "single_column")
        assert strategy == "strategy_a"


class TestDomainClassifier:
    """Test Domain Classifier (Task 4)"""
    
    def test_keyword_classifier_financial(self):
        """Test keyword classifier detects financial documents"""
        classifier = KeywordClassifier()
        text = "The company reported revenue of $10M with total assets of $50M"
        domain, confidence = classifier.classify(text)
        assert domain == "financial"
        assert confidence > 0.0
    
    def test_keyword_classifier_legal(self):
        """Test keyword classifier detects legal documents"""
        classifier = KeywordClassifier()
        text = "This agreement between parties shall be governed by arbitration clause"
        domain, confidence = classifier.classify(text)
        assert domain == "legal"
        assert confidence > 0.0
    
    def test_keyword_classifier_financial(self):
        """Test keyword classifier detects financial documents"""
        classifier = KeywordClassifier()
        text = "The company reported revenue of $10M with total assets of $50M and liabilities of $30M. The balance sheet shows strong equity and cash flow. Annual report includes EBITDA and fiscal quarter data."
        domain, confidence = classifier.classify(text)
        assert domain == "financial"
        assert confidence > 0.0
    
    def test_pluggable_strategy(self):
        """Test domain classifier is pluggable"""
        # Keyword strategy
        classifier1 = DomainClassifier(strategy="keyword")
        domain1, _ = classifier1.classify("revenue assets liabilities equity balance sheet")
        assert domain1 == "financial"
        
        # VLM strategy (mock)
        classifier2 = DomainClassifier(strategy="vlm")
        domain2, confidence2 = classifier2.classify("revenue assets")
        assert domain2 == "financial"
        assert confidence2 == 0.9


class TestIntegration:
    """Integration tests for complete triage pipeline"""
    
    def test_end_to_end_triage(self):
        """Test complete triage pipeline on known document"""
        test_pdf = "data/chunk_tax/tax_expenditure_ethiopia_2021_22_pt_1.pdf"
        
        from pathlib import Path
        if Path(test_pdf).exists():
            agent = TriageAgent()
            profile = agent.analyze(test_pdf)
            
            assert isinstance(profile, DocumentProfile)
            assert profile.origin_type in ["native_digital", "scanned_image", "mixed"]
            assert profile.layout_complexity in ["single_column", "multi_column", "table_heavy"]
            assert profile.domain_hint in ["financial", "legal", "technical", "medical", "general"]
            assert 0.0 <= profile.confidence_score <= 1.0
        else:
            pytest.skip("Test PDF not found")


# Run with: uv run pytest tests/test_triage.py -v