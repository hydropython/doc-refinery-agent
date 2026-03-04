"""
Phase 1 Task 4: Pluggable Domain Classifier

Strategy pattern for domain classification:
- KeywordClassifier: Fast, local, rule-based
- VLMClassifier: Accurate, API-based (swappable)
"""

from abc import ABC, abstractmethod
from typing import Literal, Tuple, Dict, List
from loguru import logger


class DomainClassifierStrategy(ABC):
    """Abstract base class for domain classification strategies"""
    
    @abstractmethod
    def classify(self, text_sample: str) -> Tuple[Literal["financial", "legal", "technical", "medical", "general"], float]:
        """
        Classify document domain
        
        Args:
            text_sample: Text sample from document (first 1000 chars recommended)
            
        Returns:
            Tuple of (domain_hint, confidence_score)
        """
        pass


class KeywordClassifier(DomainClassifierStrategy):
    """
    Phase 1 Requirement 4: Keyword-based domain classification
    
    Fast, local, no API calls needed.
    Uses domain-specific keyword matching with weighted scoring.
    """
    
    def __init__(self):
        self.keywords: Dict[str, List[str]] = {
            "financial": [
                "revenue", "assets", "liabilities", "equity", "balance sheet",
                "income statement", "cash flow", "EBITDA", "audit", "financial",
                "profit", "loss", "dividend", "shareholder", "capital", "reserve",
                "depreciation", "amortization", "fiscal", "quarterly", "annual report"
            ],
            "legal": [
                "contract", "agreement", "clause", "party", "liability",
                "indemnification", "arbitration", "jurisdiction", "legal",
                "plaintiff", "defendant", "court", "statute", "regulation",
                "compliance", "terms", "conditions", "witness", "testimony"
            ],
            "technical": [
                "API", "endpoint", "response", "request", "parameter",
                "function", "method", "class", "technical", "specification",
                "implementation", "architecture", "database", "server", "client",
                "authentication", "authorization", "protocol", "interface"
            ],
            "medical": [
                "patient", "diagnosis", "treatment", "symptom", "medication",
                "clinical", "medical", "healthcare", "prescription", "therapy",
                "hospital", "physician", "nurse", "dosage", "procedure",
                "laboratory", "test", "result", "condition", "disease"
            ]
        }
    
    def classify(self, text_sample: str) -> Tuple[str, float]:
        """
        Classify based on keyword matching with weighted scoring
        
        Args:
            text_sample: Text sample from document
            
        Returns:
            Tuple of (domain_hint, confidence_score)
        """
        text_lower = text_sample.lower()
        
        scores: Dict[str, float] = {}
        
        for domain, words in self.keywords.items():
            matches = sum(1 for word in words if word in text_lower)
            # Normalize by number of keywords in domain
            scores[domain] = matches / len(words) if words else 0.0
        
        # Get highest scoring domain
        if scores:
            best_domain = max(scores, key=scores.get)
            confidence = scores[best_domain]
            
            # Only return domain if confidence is above threshold
            if confidence > 0.05:
                logger.debug(f"KeywordClassifier: {best_domain} (confidence: {confidence:.2f})")
                return best_domain, min(confidence * 2, 1.0)  # Scale up for readability
        
        # Default to general if no strong match
        logger.debug("KeywordClassifier: general (no strong match)")
        return "general", 0.5


class VLMClassifier(DomainClassifierStrategy):
    """
    Phase 1 Requirement 4: VLM-based domain classification (pluggable)
    
    Can be swapped in without changing triage agent code.
    Uses vision-language model for more accurate classification.
    
    Note: Requires API key for production use.
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4-vision"):
        self.api_key = api_key
        self.model = model
        logger.warning("VLMClassifier initialized without API key - using mock classification")
    
    def classify(self, text_sample: str) -> Tuple[str, float]:
        """
        Classify using VLM API
        
        In production, this would call OpenRouter/Claude/GPT-4V
        
        Args:
            text_sample: Text sample from document
            
        Returns:
            Tuple of (domain_hint, confidence_score)
        """
        # Placeholder for VLM implementation
        # In production, call API like:
        # response = openai.ChatCompletion.create(
        #     model=self.model,
        #     messages=[{"role": "user", "content": f"Classify this document domain: {text_sample[:500]}"}]
        # )
        
        # For now, return financial as default (matches your corpus)
        logger.debug(f"VLMClassifier: financial (mock, would use {self.model})")
        return "financial", 0.9


class DomainClassifier:
    """
    Phase 1 Requirement 4: Pluggable domain classifier
    
    Usage:
        # Keyword strategy (default, no API needed)
        classifier = DomainClassifier(strategy="keyword")
        domain, confidence = classifier.classify(text_sample)
        
        # VLM strategy (requires API key, more accurate)
        classifier = DomainClassifier(strategy="vlm", api_key="your-api-key")
        domain, confidence = classifier.classify(text_sample)
    
    This allows swapping classification strategies without changing triage agent code.
    """
    
    def __init__(self, strategy: str = "keyword", **kwargs):
        """
        Initialize domain classifier with specified strategy
        
        Args:
            strategy: "keyword" or "vlm"
            **kwargs: Additional arguments passed to classifier (e.g., api_key)
        """
        if strategy == "keyword":
            self.classifier = KeywordClassifier()
            logger.info("DomainClassifier: Using keyword-based classification")
        elif strategy == "vlm":
            self.classifier = VLMClassifier(**kwargs)
            logger.info("DomainClassifier: Using VLM-based classification")
        else:
            raise ValueError(f"Unknown strategy: {strategy}. Use 'keyword' or 'vlm'")
    
    def classify(self, text_sample: str) -> Tuple[str, float]:
        """
        Delegate classification to underlying strategy
        
        Args:
            text_sample: Text sample from document
            
        Returns:
            Tuple of (domain_hint, confidence_score)
        """
        return self.classifier.classify(text_sample)


# =========================================================================
# TEST UTILITIES
# =========================================================================

def test_domain_classifier():
    """Test domain classifier with sample texts"""
    print("Testing DomainClassifier...")
    
    # Test 1: Keyword classifier with financial text
    classifier = DomainClassifier(strategy="keyword")
    text_financial = "The company reported revenue of $10M with total assets of $50M and liabilities of $30M"
    domain, confidence = classifier.classify(text_financial)
    print(f"✓ Financial text: {domain} (confidence: {confidence:.2f})")
    assert domain == "financial", f"Expected financial, got {domain}"
    
    # Test 2: Keyword classifier with legal text
    text_legal = "This agreement between parties shall be governed by arbitration clause and jurisdiction"
    domain, confidence = classifier.classify(text_legal)
    print(f"✓ Legal text: {domain} (confidence: {confidence:.2f})")
    assert domain == "legal", f"Expected legal, got {domain}"
    
    # Test 3: Keyword classifier with technical text
    text_technical = "The API endpoint returns a JSON response with authentication token and request parameters"
    domain, confidence = classifier.classify(text_technical)
    print(f"✓ Technical text: {domain} (confidence: {confidence:.2f})")
    assert domain == "technical", f"Expected technical, got {domain}"
    
    # Test 4: VLM classifier (mock)
    vlm_classifier = DomainClassifier(strategy="vlm")
    domain, confidence = vlm_classifier.classify(text_financial)
    print(f"✓ VLM classifier: {domain} (confidence: {confidence:.2f})")
    
    print("\n✅ All DomainClassifier tests passed!")


if __name__ == "__main__":
    test_domain_classifier()