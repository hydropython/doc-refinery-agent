"""
LangGraph State Schema
Location: src/graph/state.py
"""

from typing import TypedDict, List, Dict, Optional


class DocumentState(TypedDict, total=False):
    """State that flows through the LangGraph pipeline"""
    
    # Input
    doc_id: str
    pdf_path: str
    pages: List[int]
    
    # Stage 1: Triage
    page_type: str
    triage_confidence: float
    selected_strategy: str
    
    # Stage 2: Extraction
    extracted_text: str
    char_count: int
    extraction_quality: float
    extraction_confidence: float
    
    # Stage 3: Chunking
    ldus: List[Dict]
    
    # Stage 4: PageIndex
    sections: List[Dict]
    
    # Stage 5: Summaries
    summaries: List[Dict]
    
    # Stage 6: Query
    query: str
    answer: str
    provenance: Dict
    
    # Metadata
    timestamp: str
    status: str
    errors: List[str]
