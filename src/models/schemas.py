"""
Core Pydantic Schemas for Document Intelligence Refinery

All models for:
- Document profiling
- Normalized extraction output
- Logical document units (LDUs)
- Hierarchical page/section indexing
- Provenance citation chains
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator


# =============================================================================
# ENUMS FOR CATEGORICAL FIELDS
# =============================================================================

class OriginType(str, Enum):
    """Document origin type classification"""
    NATIVE_DIGITAL = "native_digital"
    SCANNED_IMAGE = "scanned_image"
    MIXED = "mixed"
    FORM_FILLABLE = "form_fillable"


class LayoutComplexity(str, Enum):
    """Document layout complexity classification"""
    SINGLE_COLUMN = "single_column"
    MULTI_COLUMN = "multi_column"
    TABLE_HEAVY = "table_heavy"
    FIGURE_HEAVY = "figure_heavy"
    MIXED = "mixed"


class DomainHint(str, Enum):
    """Document domain classification"""
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"
    MEDICAL = "medical"
    GENERAL = "general"


class ChunkType(str, Enum):
    """Chunk type for LDUs"""
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    LIST = "list"
    HEADER = "header"


# =============================================================================
# STRUCTURED SUB-MODELS
# =============================================================================

class BoundingBox(BaseModel):
    """
    Bounding box as structured sub-model (not raw list)
    
    Coordinates in points (1/72 inch)
    """
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def area(self) -> float:
        """Calculate bounding box area"""
        return (self.x1 - self.x0) * (self.y1 - self.y0)
    
    @property
    def to_list(self) -> List[float]:
        """Convert to list format"""
        return [self.x0, self.y0, self.x1, self.y1]
    
    @classmethod
    def from_list(cls, coords: List[float]) -> 'BoundingBox':
        """Create from list format"""
        return cls(x0=coords[0], y0=coords[1], x1=coords[2], y1=coords[3])


# =============================================================================
# PHASE 1: DOCUMENT PROFILING
# =============================================================================

class DocumentProfile(BaseModel):
    """
    Complete document profile from Triage Agent
    
    Used for:
    - Strategy selection
    - Cost estimation
    - Routing decisions
    """
    doc_id: str
    filename: str
    file_path: str
    origin_type: OriginType  # ✅ Enum
    layout_complexity: LayoutComplexity  # ✅ Enum
    domain_hint: DomainHint  # ✅ Enum
    domain_confidence: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommended_strategy: str
    estimated_cost_tier: str
    
    # Signal fields (from pdfplumber analysis)
    text_chars: int = 0
    vector_chars: int = 0
    images_found: int = 0
    page_count: int = 0
    page_area: float = 0.0
    char_density: float = 0.0
    image_area_ratio: float = 0.0
    column_count: int = 1
    table_count: int = 0
    figure_count: int = 0
    table_bboxes: List[List[float]] = []
    figure_bboxes: List[List[float]] = []
    has_font_meta: bool = False
    font_names: List[str] = []
    embedded_fonts: int = 0
    
    @validator('text_chars')
    def text_chars_non_negative(cls, v):
        """Ensure text_chars is non-negative"""
        if v < 0:
            raise ValueError('text_chars must be non-negative')
        return v
    
    @validator('confidence_score', 'domain_confidence')
    def confidence_in_range(cls, v):
        """Ensure confidence is between 0 and 1"""
        if not (0.0 <= v <= 1.0):
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v
    
    def validate_origin_type(self) -> bool:
        """Validate origin type matches signals"""
        if self.origin_type == OriginType.NATIVE_DIGITAL:
            return self.text_chars > 1000 and self.has_font_meta
        elif self.origin_type == OriginType.SCANNED_IMAGE:
            return self.text_chars < 50 and self.images_found >= 1
        return True
    
    def validate_layout_complexity(self) -> bool:
        """Validate layout complexity matches signals"""
        if self.layout_complexity == LayoutComplexity.TABLE_HEAVY:
            return self.table_count > 2
        elif self.layout_complexity == LayoutComplexity.MULTI_COLUMN:
            return self.column_count > 1
        return True
    
    def get_strategy_name(self) -> str:
        """Get human-readable strategy name"""
        mapping = {
            "strategy_a": "Strategy A (Fast Text)",
            "strategy_b": "Strategy B (Layout-Aware)",
            "strategy_c": "Strategy C (VLM/OCR)"
        }
        return mapping.get(self.recommended_strategy, "Unknown")


# =============================================================================
# PHASE 2: EXTRACTION OUTPUT
# =============================================================================

class ExtractedDocument(BaseModel):
    """
    Normalized extraction output from any strategy
    
    All strategies (A/B/C) output this schema.
    Used for:
    - Chunking input
    - Quality assessment
    - Provenance tracking
    """
    doc_id: str
    source_path: str
    content: str
    tables: List[Dict[str, Any]] = []
    figures: List[Dict[str, Any]] = []
    page_markers: List[int] = []
    extraction_strategy: str
    quality_score: float = Field(ge=0.0, le=1.0)
    
    @validator('quality_score')
    def quality_in_range(cls, v):
        """Ensure quality score is between 0 and 1"""
        if not (0.0 <= v <= 1.0):
            raise ValueError('Quality score must be between 0.0 and 1.0')
        return v


# =============================================================================
# PHASE 3: SEMANTIC CHUNKING
# =============================================================================

class LogicalDocumentUnit(BaseModel):
    """
    Logical Document Unit (LDU) - Semantic chunk
    
    Represents a semantically coherent unit of content.
    All 5 chunking rules enforced:
    1. Table cells never split from headers
    2. Figure captions stored as metadata
    3. Numbered lists kept as single LDU
    4. Section headers as parent metadata
    5. Cross-references resolved
    
    PROVENANCE FIELDS:
    - content_hash (SHA256)
    - page_refs
    - bounding_box
    """
    content: str
    chunk_type: ChunkType  # ✅ Enum
    page_refs: List[int]
    bounding_box: Optional[BoundingBox] = None  # ✅ Sub-model
    parent_section: str
    token_count: int
    content_hash: str  # ✅ SHA256 hash
    source_doc: str
    relationships: Optional[List[str]] = None  # ✅ Cross-refs
    
    @validator('token_count')
    def token_count_non_negative(cls, v):
        """Ensure token count is non-negative"""
        if v < 0:
            raise ValueError('token_count must be non-negative')
        return v


# =============================================================================
# PHASE 4: PAGEINDEX & QUERY
# =============================================================================

class SectionIndex(BaseModel):
    """
    Section in PageIndex tree
    
    RECURSIVE: Can contain child_sections for nested hierarchy
    """
    title: str
    page_start: int
    page_end: int
    summary: str = ""
    key_entities: List[str] = []
    data_types: List[str] = []
    ldu_count: int = 0
    token_count: int = 0
    child_sections: Optional[List['SectionIndex']] = None  # ✅ Recursive
    
    @validator('page_start', 'page_end')
    def pages_positive(cls, v):
        """Ensure page numbers are positive"""
        if v < 1:
            raise ValueError('Page numbers must be >= 1')
        return v


class PageIndex(BaseModel):
    """
    Complete document index for navigation
    
    Hierarchical tree structure for "navigation-before-retrieval"
    """
    doc_id: str
    source_path: str
    total_pages: int
    sections: List[SectionIndex]
    total_ldus: int
    total_tokens: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "doc_id": self.doc_id,
            "source_path": self.source_path,
            "total_pages": self.total_pages,
            "sections": [
                {
                    "title": s.title,
                    "page_range": f"{s.page_start}-{s.page_end}",
                    "summary": s.summary,
                    "key_entities": s.key_entities,
                    "data_types": s.data_types,
                    "ldu_count": s.ldu_count,
                    "token_count": s.token_count
                }
                for s in self.sections
            ],
            "total_ldus": self.total_ldus,
            "total_tokens": self.total_tokens
        }


# =============================================================================
# PROVENANCE CHAIN
# =============================================================================

class ProvenanceChain(BaseModel):
    """
    Provenance citation chain for audit trail
    
    Every answer must include this with:
    - document_name
    - page_number
    - bounding_box
    - content_hash
    """
    document_name: str
    page_number: int
    bounding_box: Optional[BoundingBox] = None  # ✅ Sub-model
    content_hash: str  # ✅ SHA256 hash
    extraction_strategy: str
    
    @validator('page_number')
    def page_positive(cls, v):
        """Ensure page number is positive"""
        if v < 1:
            raise ValueError('Page number must be >= 1')
        return v


# =============================================================================
# TEST UTILITIES
# =============================================================================

def create_test_profile(
    origin_type: str = "native_digital",
    layout_complexity: str = "single_column",
    text_chars: int = 5000,
    images_found: int = 0,
    **kwargs
) -> DocumentProfile:
    """Create a test DocumentProfile with defaults"""
    return DocumentProfile(
        doc_id="test_doc",
        filename="test.pdf",
        file_path="/path/test.pdf",
        origin_type=origin_type,
        layout_complexity=layout_complexity,
        domain_hint="financial",
        domain_confidence=0.9,
        confidence_score=0.95,
        recommended_strategy="strategy_a",
        estimated_cost_tier="fast_text",
        text_chars=text_chars,
        images_found=images_found,
        page_count=10,
        has_font_meta=True,
        **kwargs
    )


# =============================================================================
# SCHEMA VALIDATION TEST
# =============================================================================

def test_schemas():
    """Test all schema models"""
    print("Testing schemas...")
    
    # Test DocumentProfile
    profile = create_test_profile()
    assert profile.origin_type == OriginType.NATIVE_DIGITAL
    assert profile.validate_origin_type()
    print("✓ DocumentProfile OK")
    
    # Test ExtractedDocument
    doc = ExtractedDocument(
        doc_id="test",
        source_path="/path/test.pdf",
        content="Test content",
        extraction_strategy="strategy_a",
        quality_score=0.95
    )
    print("✓ ExtractedDocument OK")
    
    # Test LogicalDocumentUnit
    bbox = BoundingBox(x0=100, y0=200, x1=300, y1=400)
    ldu = LogicalDocumentUnit(
        content="Test chunk",
        chunk_type=ChunkType.TEXT,
        page_refs=[1, 2],
        bounding_box=bbox,
        parent_section="Introduction",
        token_count=50,
        content_hash="abc123",
        source_doc="test_doc"
    )
    assert ldu.bounding_box.area == 40000
    print("✓ LogicalDocumentUnit OK")
    
    # Test SectionIndex (recursive)
    child = SectionIndex(title="Child", page_start=1, page_end=2)
    parent = SectionIndex(
        title="Parent",
        page_start=1,
        page_end=5,
        child_sections=[child]
    )
    assert len(parent.child_sections) == 1
    print("✓ SectionIndex OK")
    
    # Test PageIndex
    page_index = PageIndex(
        doc_id="test",
        source_path="/path/test.pdf",
        total_pages=10,
        sections=[parent],
        total_ldus=5,
        total_tokens=500
    )
    print("✓ PageIndex OK")
    
    # Test ProvenanceChain
    prov = ProvenanceChain(
        document_name="test.pdf",
        page_number=5,
        bounding_box=bbox,
        content_hash="abc123",
        extraction_strategy="strategy_a"
    )
    print("✓ ProvenanceChain OK")
    
    print("\n✅ All schemas validated!")


if __name__ == "__main__":
    test_schemas()