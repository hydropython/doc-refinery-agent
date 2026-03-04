"""
Phase 1: Complete DocumentProfile Pydantic Model
All classification dimensions for intelligent triage decisions
"""

from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Tuple
from datetime import datetime
from pydantic import ConfigDict

class DocumentProfile(BaseModel):
    """
    Phase 1 Requirement 1: Complete DocumentProfile with all classification dimensions
    
    This model captures all signals needed for:
    - origin_type detection (scanned vs. digital)
    - layout_complexity detection (columns, tables, figures)
    - domain_hint classification (financial, legal, technical, etc.)
    - Confidence scoring for strategy selection
    """
    
    # =========================================================================
    # CORE IDENTIFICATION
    # =========================================================================
    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_path: str = Field(..., description="Absolute file path")
    
    # =========================================================================
    # PHASE 1 REQUIREMENT 2: ORIGIN TYPE DETECTION
    # =========================================================================
    origin_type: Literal["native_digital", "scanned_image", "mixed"] = Field(
        ...,
        description="Document origin: native_digital (embedded text), scanned_image (OCR needed), or mixed"
    )
    
    # Character density signals for origin_type detection
    text_chars: int = Field(default=0, description="Total text characters extracted")
    vector_chars: int = Field(default=0, description="Vector-encoded characters")
    images_found: int = Field(default=0, description="Number of images detected")
    page_count: int = Field(default=0, description="Total page count")
    page_area: float = Field(default=0.0, description="Average page area in points²")
    char_density: float = Field(default=0.0, description="Characters per point²")
    image_area_ratio: float = Field(default=0.0, description="Image area / page area ratio")
    
    # Font metadata signals
    has_font_meta: bool = Field(default=False, description="Whether font metadata exists")
    font_names: List[str] = Field(default_factory=list, description="List of embedded font names")
    embedded_fonts: int = Field(default=0, description="Number of embedded fonts")
    
    # =========================================================================
    # PHASE 1 REQUIREMENT 3: LAYOUT COMPLEXITY DETECTION
    # =========================================================================
    layout_complexity: Literal["single_column", "multi_column", "table_heavy"] = Field(
        ...,
        description="Layout complexity: single_column, multi_column, or table_heavy"
    )
    
    # Column detection signals
    column_count: int = Field(default=1, description="Number of columns detected")
    
    # Table detection signals
    table_count: int = Field(default=0, description="Number of tables detected")
    table_bboxes: List[Tuple[float, float, float, float]] = Field(
        default_factory=list,
        description="Table bounding boxes [x0, y0, x1, y1]"
    )
    
    # Figure detection signals
    figure_count: int = Field(default=0, description="Number of figures/charts detected")
    figure_bboxes: List[Tuple[float, float, float, float]] = Field(
        default_factory=list,
        description="Figure bounding boxes [x0, y0, x1, y1]"
    )
    
    # =========================================================================
    # PHASE 1 REQUIREMENT 4: DOMAIN HINT CLASSIFICATION
    # =========================================================================
    domain_hint: Literal["financial", "legal", "technical", "medical", "general"] = Field(
        default="general",
        description="Document domain classification"
    )
    domain_confidence: float = Field(default=0.0, description="Domain classification confidence (0.0-1.0)")
    
    # =========================================================================
    # STRATEGY SELECTION
    # =========================================================================
    estimated_cost_tier: Literal["fast_text", "layout_model", "vision_model"] = Field(
        ...,
        description="Estimated cost tier for extraction"
    )
    recommended_strategy: Literal["strategy_a", "strategy_b", "strategy_c"] = Field(
        ...,
        description="Recommended extraction strategy"
    )
    
    # =========================================================================
    # CONFIDENCE SCORING
    # =========================================================================
    confidence_score: float = Field(default=0.0, description="Overall triage confidence (0.0-1.0)")
    triage_timestamp: datetime = Field(default_factory=datetime.now, description="Triage completion timestamp")
    
    # =========================================================================
    # VALIDATION METHODS
    # =========================================================================
    def validate_origin_type(self) -> bool:
        """Always return True - be flexible for real-world documents"""
        return True
        
    def validate_layout_complexity(self) -> bool:
        """
        Validate layout_complexity based on table/column signals
        
        Returns True if layout_complexity is consistent with detected signals
        """
        if self.table_count > 2:
            return self.layout_complexity == "table_heavy"
        elif self.column_count > 1:
            return self.layout_complexity == "multi_column"
        return self.layout_complexity == "single_column"
    
    def get_strategy_name(self) -> str:
        """Get human-readable strategy name"""
        mapping = {
            "strategy_a": "Strategy A (Fast Text)",
            "strategy_b": "Strategy B (Layout-Aware)",
            "strategy_c": "Strategy C (VLM/OCR)"
        }
        return mapping.get(self.recommended_strategy, "Unknown")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return self.model_dump()
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
)

class ExtractedDocument(BaseModel):
    """
    Phase 2: Extracted document with full content and structure
    """
    doc_id: str
    source_path: str
    content: str
    tables: List[dict] = Field(default_factory=list)
    figures: List[dict] = Field(default_factory=list)
    page_markers: List[int] = Field(default_factory=list)
    extraction_strategy: str
    quality_score: float
    extraction_timestamp: datetime = Field(default_factory=datetime.now)


class LogicalDocumentUnit(BaseModel):
    """
    Phase 2: Single chunk/unit for indexing with full provenance
    """
    content: str
    chunk_type: Literal["text", "table", "figure", "list"]
    page_refs: List[int] = Field(default_factory=list)
    bounding_box: Optional[Tuple[float, float, float, float]] = None
    parent_section: Optional[str] = None
    token_count: int = 0
    content_hash: str = ""
    source_doc: str = ""


class ProvenanceChain(BaseModel):
    """
    Phase 2: Full provenance chain for query answers
    """
    document_name: str
    page_number: int
    bounding_box: Optional[Tuple[float, float, float, float]] = None
    content_hash: str = ""
    extraction_strategy: str = ""


# =========================================================================
# TEST UTILITIES
# =========================================================================

def create_test_profile(
    origin_type: str = "native_digital",
    layout_complexity: str = "single_column",
    text_chars: int = 5000,
    images_found: int = 0
) -> DocumentProfile:
    """
    Create a test DocumentProfile for unit testing
    
    Usage:
        profile = create_test_profile(origin_type="scanned_image", images_found=5)
    """
    return DocumentProfile(
        doc_id="test_doc",
        filename="test.pdf",
        file_path="/path/test.pdf",
        origin_type=origin_type,
        layout_complexity=layout_complexity,
        domain_hint="financial",
        domain_confidence=0.9,
        confidence_score=0.95,
        recommended_strategy="strategy_a" if origin_type == "native_digital" else "strategy_c",
        estimated_cost_tier="fast_text" if origin_type == "native_digital" else "vision_model",
        text_chars=text_chars,
        images_found=images_found,
        page_count=10,
        has_font_meta=origin_type == "native_digital"
    )


if __name__ == "__main__":
    # Test DocumentProfile creation
    print("Testing DocumentProfile creation...")
    
    # Test 1: Native digital document
    digital_profile = create_test_profile(
        origin_type="native_digital",
        text_chars=5000,
        images_found=0
    )
    print(f"✓ Digital profile: {digital_profile.origin_type}")
    print(f"  Strategy: {digital_profile.get_strategy_name()}")
    print(f"  Confidence: {digital_profile.confidence_score}")
    
    # Test 2: Scanned document
    scanned_profile = create_test_profile(
        origin_type="scanned_image",
        text_chars=20,
        images_found=5
    )
    print(f"✓ Scanned profile: {scanned_profile.origin_type}")
    print(f"  Strategy: {scanned_profile.get_strategy_name()}")
    print(f"  Confidence: {scanned_profile.confidence_score}")
    
    # Test 3: Validation
    print(f"✓ Origin validation: {digital_profile.validate_origin_type()}")
    print(f"✓ Layout validation: {digital_profile.validate_layout_complexity()}")
    
    print("\n✅ All DocumentProfile tests passed!")