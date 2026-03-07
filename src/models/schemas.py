"""
Document Schemas - WITH PROVENANCE CHAIN
Location: src/models/schemas.py
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from datetime import datetime
from enum import Enum
import hashlib


# ========== ENUMS (Required by other modules) ==========

class OriginType(str, Enum):
    NATIVE_DIGITAL = "native_digital"
    SCANNED_IMAGE = "scanned_image"
    MIXED = "mixed"


class LayoutComplexity(str, Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    TABLE_HEAVY = "table_heavy"
    IMAGE_HEAVY = "image_heavy"


class DomainHint(str, Enum):
    FINANCIAL = "financial"
    LEGAL = "legal"
    TECHNICAL = "technical"
    GENERAL = "general"


# ========== DATA MODELS ==========

class DocumentProfile(BaseModel):
    """Document profile from triage analysis"""
    origin_type: OriginType
    layout_complexity: LayoutComplexity
    recommended_strategy: str
    confidence_score: float
    text_chars: int
    images_found: int
    table_count: int
    page_count: int
    char_density: float
    has_font_meta: bool
    embedded_fonts: int
    estimated_cost_tier: str


class ProvenanceItem(BaseModel):
    """Provenance tracking for extracted content"""
    page: int
    bbox: Optional[Tuple[float, float, float, float]] = None
    content_hash: str
    source_type: str
    char_count: int
    extracted_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    @staticmethod
    def generate_hash(content: str) -> str:
        """Generate SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


class ExtractedDocument(BaseModel):
    """Extracted document with provenance chain"""
    doc_id: str
    content: str
    source_path: str
    page_markers: List[int]
    quality_score: float
    extraction_strategy: str
    provenance_chain: List[ProvenanceItem] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
    
    def add_provenance(self, page: int, content: str, source_type: str, 
                       bbox: Optional[Tuple] = None):
        """Add provenance item for extracted content"""
        item = ProvenanceItem(
            page=page,
            bbox=bbox,
            content_hash=ProvenanceItem.generate_hash(content),
            source_type=source_type,
            char_count=len(content)
        )
        self.provenance_chain.append(item)
        return item


class LDU(BaseModel):
    """Logical Document Unit"""
    id: str
    page: int
    section: str
    content: str
    metadata: dict = Field(default_factory=dict)


class SectionNode(BaseModel):
    """Section in PageIndex"""
    title: str
    pages: List[int]
    ldus: List[LDU] = Field(default_factory=list)
    summary: str = ""
