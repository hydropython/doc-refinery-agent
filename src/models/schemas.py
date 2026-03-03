from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class DocumentProfile(BaseModel):
    doc_id: str
    origin_type: str  # native_digital | scanned_image
    layout_complexity: str  # single_column | multi_column | table_heavy
    estimated_cost_tier: str # fast_text | layout_model | vision_model
    metadata: Dict[str, Any]

class Table(BaseModel):
    headers: List[str]
    rows: List[List[Any]]
    page_ref: int

class ExtractedDocument(BaseModel):
    doc_id: str
    text_content: str
    tables: List[Table]
    strategy_used: str
    confidence_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)