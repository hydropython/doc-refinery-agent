"""
Phase 2: Integration Tests

Tests the complete pipeline:
Triage → Router → Strategies → Chunking → PageIndex → Query
"""

import pytest
from src.models.schemas import DocumentProfile, LogicalDocumentUnit
from src.agents.triage import TriageAgent
from src.agents.query_agent import QueryAgent
from src.chunker.semantic_chunker import SemanticChunker
from src.chunker.page_index import PageIndexBuilder, SectionIndex
from src.vector_store.vector_db import VectorStore, get_vector_store


class TestSemanticChunker:
    """Test Semantic Chunking Engine"""
    
    def test_chunker_initialization(self):
        """Test chunker can be initialized"""
        chunker = SemanticChunker()
        assert chunker.max_chunk_size == 512
        assert chunker.overlap == 50
    
    def test_chunker_statistics(self):
        """Test statistics generation"""
        chunker = SemanticChunker()
        
        # Create mock LDUs
        ldus = [
            LogicalDocumentUnit(
                content="Test content 1",
                chunk_type="text",
                page_refs=[1],
                parent_section="Section 1",
                token_count=100,
                content_hash="abc123",
                source_doc="test_doc"
            ),
            LogicalDocumentUnit(
                content="Test content 2",
                chunk_type="table",
                page_refs=[2],
                parent_section="Section 2",
                token_count=200,
                content_hash="def456",
                source_doc="test_doc"
            )
        ]
        
        stats = chunker.get_statistics(ldus)
        assert stats["total_ldus"] == 2
        assert stats["total_tokens"] == 300
        assert "text" in stats["by_type"]
        assert "table" in stats["by_type"]


class TestPageIndexBuilder:
    """Test PageIndex Builder"""
    
    def test_builder_initialization(self):
        """Test builder can be initialized"""
        builder = PageIndexBuilder()
        assert builder is not None
    
    def test_build_page_index(self):
        """Test PageIndex construction"""
        builder = PageIndexBuilder()
        
        # Create mock LDUs
        ldus = [
            LogicalDocumentUnit(
                content="Introduction content",
                chunk_type="text",
                page_refs=[1, 2],
                parent_section="Introduction",
                token_count=150,
                content_hash="abc123",
                source_doc="test_doc"
            ),
            LogicalDocumentUnit(
                content="Financial data content",
                chunk_type="text",
                page_refs=[3, 4, 5],
                parent_section="Financial Data",
                token_count=300,
                content_hash="def456",
                source_doc="test_doc"
            )
        ]
        
        # Build index
        page_index = builder.build(ldus, "/path/test.pdf", 5)
        
        assert page_index.doc_id == "test_doc"
        assert page_index.total_pages == 5
        assert len(page_index.sections) == 2
        assert page_index.total_ldus == 2
        assert page_index.total_tokens == 450
    
    def test_navigate_to_section(self):
        """Test section navigation"""
        builder = PageIndexBuilder()
        
        ldus = [
            LogicalDocumentUnit(
                content="Financial content",
                chunk_type="text",
                page_refs=[1],
                parent_section="Financial Data",
                token_count=100,
                content_hash="abc123",
                source_doc="test_doc"
            )
        ]
        
        page_index = builder.build(ldus, "/path/test.pdf", 3)
        
        # Navigate to section
        section = builder.navigate(page_index, "financial")
        assert section is not None
        assert section.title == "Financial Data"


class TestQueryAgent:
    """Test Query Interface Agent"""
    
    def test_agent_initialization(self):
        """Test agent can be initialized"""
        agent = QueryAgent()
        assert agent is not None
    
    def test_register_document(self):
        """Test document registration"""
        agent = QueryAgent()
        
        # Create mock data
        ldus = [
            LogicalDocumentUnit(
                content="Revenue increased by 10% in Q4",
                chunk_type="text",
                page_refs=[1],
                parent_section="Financial Results",
                token_count=50,
                content_hash="abc123",
                source_doc="test_doc"
            )
        ]
        
        from src.chunker.page_index import PageIndex
        page_index = PageIndex(
            doc_id="test_doc",
            source_path="/path/test.pdf",
            total_pages=5,
            sections=[],
            total_ldus=1,
            total_tokens=50
        )
        
        # Register
        agent.register_document("test_doc", page_index, ldus)
        
        stats = agent.get_statistics()
        assert stats["registered_documents"] == 1
        assert stats["total_ldus"] == 1
    
    def test_query_search(self):
        """Test query with search"""
        agent = QueryAgent()
        
        # Create mock data with financial content
        ldus = [
            LogicalDocumentUnit(
                content="The company reported revenue of $50M with assets of $100M",
                chunk_type="text",
                page_refs=[1],
                parent_section="Financial Results",
                token_count=50,
                content_hash="abc123",
                source_doc="test_doc"
            )
        ]
        
        from src.chunker.page_index import PageIndex
        page_index = PageIndex(
            doc_id="test_doc",
            source_path="/path/test.pdf",
            total_pages=5,
            sections=[],
            total_ldus=1,
            total_tokens=50
        )
        
        agent.register_document("test_doc", page_index, ldus)
        
        # Query
        # Query
        result = agent.query("revenue assets", doc_ids=["test_doc"])
        
        assert result.answer is not None
        assert len(result.sources) > 0
        assert "test_doc" in result.sources


class TestVectorStore:
    """Test Vector Store"""
    
    def test_store_initialization(self):
        """Test store can be initialized"""
        store = VectorStore()
        assert store.db_path.name == "lancedb"
    
    def test_store_connect(self):
        """Test store connection"""
        store = VectorStore()
        store.connect()
        assert store.table is not None
    
    def test_store_statistics(self):
        """Test statistics generation"""
        store = VectorStore()
        store.connect()
        
        stats = store.get_statistics()
        assert "total_ldus" in stats
        assert "db_path" in stats


class TestIntegration:
    """Integration Tests - Full Pipeline"""
    
    def test_end_to_end_pipeline(self):
        """Test complete pipeline: Triage → Chunk → Index → Query"""
        # Step 1: Triage (use existing PDF)
        test_pdf = "data/chunk_tax/tax_expenditure_ethiopia_2021_22_pt_1.pdf"
        
        from pathlib import Path
        if not Path(test_pdf).exists():
            pytest.skip("Test PDF not found")
        
        # Triage
        triage = TriageAgent()
        profile = triage.analyze(test_pdf)
        
        assert profile.origin_type in ["native_digital", "scanned_image", "mixed"]
        assert profile.layout_complexity in ["single_column", "multi_column", "table_heavy"]
        
        # Step 2: Mock extraction (would use strategies in production)
        from src.models.schemas import ExtractedDocument
        extracted = ExtractedDocument(
            doc_id=profile.doc_id,
            source_path=test_pdf,
            content="Sample extracted content for testing",
            tables=[],
            figures=[],
            page_markers=[1, 2, 3],
            extraction_strategy=profile.recommended_strategy,
            quality_score=profile.confidence_score
        )
        
        # Step 3: Chunk
        chunker = SemanticChunker()
        # In production: ldus = chunker.chunk(extracted)
        # For test, create mock LDUs
        ldus = [
            LogicalDocumentUnit(
                content="Sample content chunk 1",
                chunk_type="text",
                page_refs=[1],
                parent_section="Section 1",
                token_count=50,
                content_hash="abc123",
                source_doc=profile.doc_id
            )
        ]
        
        # Step 4: Index
        builder = PageIndexBuilder()
        page_index = builder.build(ldus, test_pdf, profile.page_count)
        
        assert page_index.doc_id == profile.doc_id
        assert len(page_index.sections) > 0
        
        # Step 5: Register for query
        agent = QueryAgent()
        agent.register_document(profile.doc_id, page_index, ldus)
        
        # Step 6: Query
        result = agent.query("sample content", doc_ids=[profile.doc_id])
        
        assert result.answer is not None
        assert len(result.provenance) > 0
        
        # Step 7: Vector store
        store = VectorStore()
        store.connect()
        
        stats = store.get_statistics()
        assert "total_ldus" in stats


# Run with: uv run pytest tests/test_phase2.py -v
