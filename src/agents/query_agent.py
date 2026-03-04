"""
Phase 2 Task 5: Query Interface Agent

Answers user questions with full provenance chain.
Uses 3 tools: Search, Navigate, Query.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from src.models.schemas import ProvenanceChain, LogicalDocumentUnit
from src.chunker.page_index import PageIndex, PageIndexBuilder
from src.chunker.semantic_chunker import SemanticChunker


@dataclass
class QueryResult:
    """Query result with answer and provenance"""
    answer: str
    confidence: float
    provenance: List[ProvenanceChain]
    sources: List[str]  # Document names
    pages: List[int]    # Page numbers


class QueryAgent:
    """
    Phase 2: Query Interface Agent
    
    Answers user questions with full provenance chain.
    Uses 3 tools for comprehensive document intelligence.
    """
    
    def __init__(self):
        logger.info("QueryAgent initialized")
        self.page_indices: Dict[str, PageIndex] = {}
        self.ldu_index: Dict[str, List[LogicalDocumentUnit]] = {}
    
    def register_document(self, doc_id: str, page_index: PageIndex, ldus: List[LogicalDocumentUnit]):
        """
        Register a document for querying
        
        Args:
            doc_id: Document identifier
            page_index: PageIndex from builder
            ldus: List of LDUs from chunker
        """
        self.page_indices[doc_id] = page_index
        self.ldu_index[doc_id] = ldus
        logger.info(f"Registered document: {doc_id} ({len(ldus)} LDUs)")
    
    def query(self, question: str, doc_ids: Optional[List[str]] = None) -> QueryResult:
        """
        Answer user question with provenance
        
        Args:
            question: User's question
            doc_ids: Optional list of document IDs to search (None = all)
            
        Returns:
            QueryResult with answer and provenance chain
        """
        logger.info(f"Query: {question}")
        
        # Determine which documents to search
        if doc_ids is None:
            doc_ids = list(self.page_indices.keys())
        
        # Tool 1: Search across LDUs
        search_results = self._search_tool(question, doc_ids)
        
        # Tool 2: Navigate to relevant sections
        nav_results = self._navigate_tool(question, doc_ids)
        
        # Tool 3: Query structured data (tables)
        query_results = self._query_tool(question, doc_ids)
        
        # Combine results
        answer, provenance = self._synthesize_answer(
            question, search_results, nav_results, query_results
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(search_results, nav_results, query_results)
        
        # Extract sources and pages
        sources = list(set(p.document_name for p in provenance))
        pages = list(set(p.page_number for p in provenance))
        
        result = QueryResult(
            answer=answer,
            confidence=confidence,
            provenance=provenance,
            sources=sources,
            pages=pages
        )
        
        logger.success(f"Answer generated (confidence: {confidence:.2f})")
        
        return result
    
    def _search_tool(self, question: str, doc_ids: List[str]) -> List[Tuple[LogicalDocumentUnit, float]]:
        """
        Tool 1: Semantic search across LDUs
        
        Returns LDUs ranked by relevance to question.
        """
        results = []
        question_lower = question.lower()
        
        for doc_id in doc_ids:
            if doc_id not in self.ldu_index:
                continue
            
            for ldu in self.ldu_index[doc_id]:
                # Simple keyword matching (would use embeddings in production)
                content_lower = ldu.content.lower()
                
                # Count keyword matches
                question_words = question_lower.split()
                matches = sum(1 for word in question_words if word in content_lower and len(word) > 3)
                score = matches / len(question_words) if question_words else 0
                
                if score > 0.1:  # Threshold
                    results.append((ldu, score))
        
        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:10]  # Top 10 results
    
    def _navigate_tool(self, question: str, doc_ids: List[str]) -> List[Tuple[str, Any]]:
        """
        Tool 2: Navigate to relevant sections
        
        Returns sections that match the query.
        """
        results = []
        
        for doc_id in doc_ids:
            if doc_id not in self.page_indices:
                continue
            
            page_index = self.page_indices[doc_id]
            
            # Search section titles
            for section in page_index.sections:
                if question.lower() in section.title.lower():
                    results.append((doc_id, section))
                
                # Search entities
                for entity in section.key_entities:
                    if question.lower() in entity.lower():
                        results.append((doc_id, section))
        
        return results
    
    def _query_tool(self, question: str, doc_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Tool 3: Query structured data (tables)
        
        Returns table data that matches the query.
        """
        results = []
        
        for doc_id in doc_ids:
            if doc_id not in self.ldu_index:
                continue
            
            for ldu in self.ldu_index[doc_id]:
                if ldu.chunk_type == "table":
                    # Check if table content matches query
                    if any(word in ldu.content.lower() for word in question.lower().split()):
                        results.append({
                            "doc_id": doc_id,
                            "table": ldu.content,
                            "page_refs": ldu.page_refs,
                            "section": ldu.parent_section
                        })
        
        return results
    
    def _synthesize_answer(
        self,
        question: str,
        search_results: List[Tuple[LogicalDocumentUnit, float]],
        nav_results: List[Tuple[str, Any]],
        query_results: List[Dict[str, Any]]
    ) -> Tuple[str, List[ProvenanceChain]]:
        """
        Synthesize answer from all tool results
        
        Returns: (answer, provenance_chain)
        """
        provenance = []
        answer_parts = []
        
        # Add search results to answer
        for ldu, score in search_results[:3]:  # Top 3
            answer_parts.append(ldu.content[:200])
            
            # Create provenance chain
            prov = ProvenanceChain(
                document_name=ldu.source_doc,
                page_number=ldu.page_refs[0] if ldu.page_refs else 1,
                bounding_box=ldu.bounding_box,
                content_hash=ldu.content_hash,
                extraction_strategy="strategy_a"  # Would track in production
            )
            provenance.append(prov)
        
        # Add table data if available
        for table_result in query_results[:2]:  # Top 2 tables
            answer_parts.append(f"[TABLE from {table_result['section']}]: {table_result['table'][:200]}")
            
            prov = ProvenanceChain(
                document_name=table_result['doc_id'],
                page_number=table_result['page_refs'][0] if table_result['page_refs'] else 1,
                bounding_box=None,
                content_hash=hashlib.sha256(table_result['table'].encode()).hexdigest()[:16],
                extraction_strategy="strategy_b"
            )
            provenance.append(prov)
        
        # Combine answer
        if answer_parts:
            answer = "\n\n".join(answer_parts)
        else:
            answer = "No relevant information found in the indexed documents."
        
        return answer, provenance
    
    def _calculate_confidence(
        self,
        search_results: List[Tuple[LogicalDocumentUnit, float]],
        nav_results: List[Tuple[str, Any]],
        query_results: List[Dict[str, Any]]
    ) -> float:
        """Calculate answer confidence score"""
        scores = []
        
        # Search score
        if search_results:
            avg_search_score = sum(s for _, s in search_results[:5]) / min(len(search_results), 5)
            scores.append(avg_search_score)
        
        # Navigation score
        if nav_results:
            scores.append(min(len(nav_results) / 5, 1.0))
        
        # Query score
        if query_results:
            scores.append(min(len(query_results) / 3, 1.0))
        
        if scores:
            return sum(scores) / len(scores)
        return 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get query agent statistics"""
        return {
            "registered_documents": len(self.page_indices),
            "total_ldus": sum(len(ldus) for ldus in self.ldu_index.values()),
            "total_sections": sum(len(pi.sections) for pi in self.page_indices.values())
        }


# Import hashlib for ProvenanceChain
import hashlib