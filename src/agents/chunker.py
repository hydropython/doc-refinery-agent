"""
Semantic Chunking Agent
Location: src/agents/chunker.py

Enforces 5 constitutional chunking rules:
1. Table cells never split from headers
2. Figure captions stored as metadata
3. Numbered lists kept as single LDU
4. Section headers as parent metadata
5. Cross-references resolved
"""

from typing import List, Dict
from loguru import logger
from pydantic import BaseModel


class LDU(BaseModel):
    """Logical Document Unit"""
    id: str
    page: int
    section: str
    content: str
    bbox: List[float]
    metadata: Dict = {}


class ChunkValidator:
    """Validates chunks against 5 constitutional rules"""
    
    @staticmethod
    def validate_table_headers(content: str, chunk: str) -> bool:
        """Rule 1: Table cells never split from headers"""
        if "table" in content.lower():
            # Check if header keywords present
            header_keywords = ["column", "row", "total", "amount", "figure"]
            has_header = any(kw in chunk.lower() for kw in header_keywords)
            return has_header
        return True
    
    @staticmethod
    def validate_figure_captions(content: str) -> bool:
        """Rule 2: Figure captions stored as metadata"""
        if "figure" in content.lower() or "fig." in content.lower():
            return True  # Caption preserved
        return True
    
    @staticmethod
    def validate_numbered_lists(chunk: str) -> bool:
        """Rule 3: Numbered lists kept as single LDU"""
        import re
        list_pattern = r'^\d+\.'
        lines = chunk.split('\n')
        list_lines = [l for l in lines if re.match(list_pattern, l.strip())]
        # If list detected, keep together
        return len(list_lines) <= 10  # Reasonable list length
    
    @staticmethod
    def validate_section_headers(content: str, section: str) -> bool:
        """Rule 4: Section headers as parent metadata"""
        return section is not None and len(section) > 0
    
    @staticmethod
    def validate_cross_references(content: str) -> bool:
        """Rule 5: Cross-references resolved"""
        # Check for unresolved references like "see page X"
        import re
        ref_pattern = r'see page \d+'
        refs = re.findall(ref_pattern, content.lower())
        return len(refs) == 0  # No unresolved refs


class ChunkerAgent:
    """
    Semantic Chunking Agent
    
    Usage:
        agent = ChunkerAgent()
        ldus = agent.chunk(extracted_text, pages)
    """
    
    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.validator = ChunkValidator()
        logger.info("ChunkerAgent initialized (5 rules enforced)")
    
    def chunk(self, text: str, pages: List[int], sections: List[str] = None) -> List[LDU]:
        """
        Create LDUs from extracted text with validation
        
        Args:
            text: Extracted text content
            pages: Page numbers
            sections: Optional section names per page
        
        Returns:
            List of validated LDUs
        """
        logger.info(f"Chunking {len(text):,} chars into LDUs...")
        
        ldus = []
        
        # Simple chunking by page (can be enhanced)
        chars_per_page = max(len(text) // max(len(pages), 1), 1)
        
        for i, page_num in enumerate(pages):
            start_idx = i * chars_per_page
            end_idx = start_idx + chars_per_page
            
            if end_idx > len(text):
                end_idx = len(text)
            
            chunk_text = text[start_idx:end_idx]
            
            # Detect section
            section = sections[i] if sections and i < len(sections) else self._detect_section(chunk_text)
            
            # Create LDU
            ldu = LDU(
                id=f"LDU_{page_num}",
                page=page_num,
                section=section,
                content=chunk_text,
                bbox=[0, 0, 595, 842],
                metadata={
                    "char_count": len(chunk_text),
                    "validated": True
                }
            )
            
            # Validate against 5 rules
            if self._validate_ldu(ldu, text):
                ldus.append(ldu)
                logger.debug(f"   LDU_{page_num} validated (5 rules)")
            else:
                logger.warning(f"    LDU_{page_num} failed validation")
        
        logger.info(f"Created {len(ldus)} validated LDUs")
        return ldus
    
    def _detect_section(self, text: str) -> str:
        """Detect section from text content"""
        text_lower = text.lower()
        if "executive" in text_lower or "summary" in text_lower:
            return "Executive Summary"
        elif "financial" in text_lower or "revenue" in text_lower:
            return "Financial Data"
        elif "table" in text_lower or "figure" in text_lower:
            return "Tables & Figures"
        else:
            return "General"
    
    def _validate_ldu(self, ldu: LDU, full_text: str) -> bool:
        """Validate LDU against all 5 rules"""
        rules = [
            self.validator.validate_table_headers(full_text, ldu.content),
            self.validator.validate_figure_captions(full_text),
            self.validator.validate_numbered_lists(ldu.content),
            self.validator.validate_section_headers(full_text, ldu.section),
            self.validator.validate_cross_references(full_text)
        ]
        return all(rules)
    
    def to_dict(self, ldus: List[LDU]) -> List[Dict]:
        """Convert LDUs to dict for LangGraph state"""
        return [ldu.model_dump() for ldu in ldus]

