"""
Phase 2 Task 4: PageIndex Builder

Builds hierarchical document index for navigation.
Each section has: title, page range, summary, key entities.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

from src.models.schemas import LogicalDocumentUnit


@dataclass
class SectionIndex:
    """Single section in the page index"""
    title: str
    page_start: int
    page_end: int
    summary: str = ""
    key_entities: List[str] = field(default_factory=list)
    data_types: List[str] = field(default_factory=list)
    ldu_count: int = 0
    token_count: int = 0


@dataclass
class PageIndex:
    """Complete document index"""
    doc_id: str
    source_path: str
    total_pages: int
    sections: List[SectionIndex] = field(default_factory=list)
    total_ldus: int = 0
    total_tokens: int = 0
    
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


class PageIndexBuilder:
    """
    Phase 2: PageIndex Builder
    
    Builds hierarchical index from LogicalDocumentUnits.
    Groups LDUs by section and calculates summaries.
    """
    
    def __init__(self):
        logger.info("PageIndexBuilder initialized")
    
    def build(self, ldus: List[LogicalDocumentUnit], source_path: str, total_pages: int) -> PageIndex:
        """
        Build PageIndex from LDUs
        
        Args:
            ldus: List of LogicalDocumentUnit from chunker
            source_path: Original document path
            total_pages: Total pages in document
            
        Returns:
            PageIndex with hierarchical structure
        """
        logger.info(f"Building PageIndex for {len(ldus)} LDUs")
        
        # Group LDUs by section
        sections_map = self._group_by_section(ldus)
        
        # Build section indices
        sections = []
        for section_title, section_ldus in sections_map.items():
            section_index = self._build_section_index(section_title, section_ldus)
            sections.append(section_index)
        
        # Sort sections by page number
        sections.sort(key=lambda s: s.page_start)
        
        # Calculate totals
        total_ldus = len(ldus)
        total_tokens = sum(ldu.token_count for ldu in ldus)
        
        # Get doc_id from first LDU
        doc_id = ldus[0].source_doc if ldus else "unknown"
        
        page_index = PageIndex(
            doc_id=doc_id,
            source_path=source_path,
            total_pages=total_pages,
            sections=sections,
            total_ldus=total_ldus,
            total_tokens=total_tokens
        )
        
        logger.success(f"PageIndex built: {len(sections)} sections, {total_ldus} LDUs")
        
        return page_index
    
    def _group_by_section(self, ldus: List[LogicalDocumentUnit]) -> Dict[str, List[LogicalDocumentUnit]]:
        """Group LDUs by parent_section"""
        sections = {}
        
        for ldu in ldus:
            section = ldu.parent_section or "Unknown"
            if section not in sections:
                sections[section] = []
            sections[section].append(ldu)
        
        return sections
    
    def _build_section_index(self, title: str, ldus: List[LogicalDocumentUnit]) -> SectionIndex:
        """Build index for single section"""
        # Calculate page range
        all_pages = []
        for ldu in ldus:
            all_pages.extend(ldu.page_refs)
        
        page_start = min(all_pages) if all_pages else 1
        page_end = max(all_pages) if all_pages else 1
        
        # Calculate token count
        token_count = sum(ldu.token_count for ldu in ldus)
        
        # Generate summary (simplified - would use LLM in production)
        summary = self._generate_summary(ldus)
        
        # Extract key entities (simplified - would use NER in production)
        key_entities = self._extract_entities(ldus)
        
        # Identify data types
        data_types = self._identify_data_types(ldus)
        
        return SectionIndex(
            title=title,
            page_start=page_start,
            page_end=page_end,
            summary=summary,
            key_entities=key_entities,
            data_types=data_types,
            ldu_count=len(ldus),
            token_count=token_count
        )
    
    def _generate_summary(self, ldus: List[LogicalDocumentUnit]) -> str:
        """Generate section summary (simplified)"""
        # Combine first 200 chars from each LDU
        texts = [ldu.content[:200] for ldu in ldus[:3]]
        combined = " ".join(texts)
        
        # Truncate to 150 chars
        if len(combined) > 150:
            combined = combined[:147] + "..."
        
        return combined
    
    def _extract_entities(self, ldus: List[LogicalDocumentUnit]) -> List[str]:
        """Extract key entities (simplified)"""
        entities = []
        
        # Look for capitalized words (potential entities)
        for ldu in ldus[:5]:  # Sample first 5 LDUs
            words = ldu.content.split()
            for word in words:
                if word[0].isupper() and len(word) > 2:
                    clean_word = word.strip('.,;:()[]"\'')
                    if clean_word not in entities and len(entities) < 10:
                        entities.append(clean_word)
        
        return entities[:10]  # Limit to 10 entities
    
    def _identify_data_types(self, ldus: List[LogicalDocumentUnit]) -> List[str]:
        """Identify data types in section"""
        data_types = set()
        
        for ldu in ldus:
            # Check for tables
            if ldu.chunk_type == "table":
                data_types.add("tables")
            
            # Check for figures
            if ldu.chunk_type == "figure":
                data_types.add("figures")
            
            # Check for lists
            if ldu.chunk_type == "list":
                data_types.add("lists")
            
            # Check for numbers (financial data)
            if any(c.isdigit() for c in ldu.content):
                data_types.add("numerical_data")
        
        return list(data_types)
    
    def navigate(self, page_index: PageIndex, query: str) -> Optional[SectionIndex]:
        """
        Navigate to section matching query
        
        Args:
            page_index: PageIndex to search
            query: Search query (section title or keyword)
            
        Returns:
            Matching SectionIndex or None
        """
        query_lower = query.lower()
        
        for section in page_index.sections:
            # Match title
            if query_lower in section.title.lower():
                return section
            
            # Match summary
            if query_lower in section.summary.lower():
                return section
            
            # Match entities
            if any(query_lower in entity.lower() for entity in section.key_entities):
                return section
        
        return None
    
    def get_statistics(self, page_index: PageIndex) -> Dict[str, Any]:
        """Get PageIndex statistics"""
        return {
            "doc_id": page_index.doc_id,
            "total_pages": page_index.total_pages,
            "total_sections": len(page_index.sections),
            "total_ldus": page_index.total_ldus,
            "total_tokens": page_index.total_tokens,
            "avg_ldus_per_section": page_index.total_ldus / len(page_index.sections) if page_index.sections else 0,
            "avg_tokens_per_section": page_index.total_tokens / len(page_index.sections) if page_index.sections else 0
        }