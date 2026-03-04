"""
Phase 2 Task 6: Vector Store Integration

Uses LanceDB for semantic search over LDUs.
Supports hybrid search (keyword + vector).
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from loguru import logger

import hashlib


class VectorStore:
    """
    Phase 2: Vector Store for LDUs
    
    Stores embeddings for semantic search.
    Uses LanceDB (local, fast, no API required).
    """
    
    def __init__(self, db_path: str = ".refinery_db/lancedb"):
        """
        Initialize vector store
        
        Args:
            db_path: Path to LanceDB database
        """
        self.db_path = Path(db_path)
        self.db = None
        self.table = None
        logger.info(f"VectorStore initialized (path: {db_path})")
    
    def connect(self):
        """Connect to LanceDB"""
        try:
            import lancedb
            self.db = lancedb.connect(self.db_path)
            
            # Create or open table
            if "ldus" not in self.db.table_names():
                self._create_table()
            else:
                self.table = self.db.open_table("ldus")
            
            logger.success("Connected to LanceDB")
            
        except ImportError:
            logger.warning("LanceDB not installed. Using in-memory store.")
            self.table = InMemoryTable()
        except Exception as e:
            logger.error(f"Failed to connect to LanceDB: {e}")
            self.table = InMemoryTable()
    
    def _create_table(self):
        """Create LDU table schema"""
        schema = {
            "id": "string",
            "content": "string",
            "vector": "vector",
            "doc_id": "string",
            "chunk_type": "string",
            "page_refs": "string",
            "parent_section": "string",
            "content_hash": "string",
            "source_doc": "string"
        }
        self.table = self.db.create_table("ldus", schema=schema)
    
    def add_ldus(self, ldus: List[Any], embeddings: Optional[List[List[float]]] = None):
        """
        Add LDUs to vector store
        
        Args:
            ldus: List of LogicalDocumentUnit
            embeddings: Optional pre-computed embeddings
        """
        if self.table is None:
            self.connect()
        
        records = []
        for i, ldu in enumerate(ldus):
            # Get or compute embedding
            if embeddings:
                vector = embeddings[i]
            else:
                vector = self._compute_embedding(ldu.content)
            
            record = {
                "id": f"{ldu.source_doc}_{i}",
                "content": ldu.content,
                "vector": vector,
                "doc_id": ldu.source_doc,
                "chunk_type": ldu.chunk_type,
                "page_refs": str(ldu.page_refs),
                "parent_section": ldu.parent_section,
                "content_hash": ldu.content_hash,
                "source_doc": ldu.source_doc
            }
            records.append(record)
        
        # Add to table
        self.table.add(records)
        logger.success(f"Added {len(records)} LDUs to vector store")
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Semantic search
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of matching LDUs with scores
        """
        if self.table is None:
            self.connect()
        
        # Compute query embedding
        query_vector = self._compute_embedding(query)
        
        # Search
        results = self.table.search(query_vector).limit(top_k).to_list()
        
        logger.info(f"Search returned {len(results)} results")
        
        return results
    
    def hybrid_search(
        self,
        query: str,
        filter_dict: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search (vector + keyword + filter)
        
        Args:
            query: Search query
            filter_dict: Optional filters (e.g., {"chunk_type": "table"})
            top_k: Number of results
            
        Returns:
            List of matching LDUs with scores
        """
        if self.table is None:
            self.connect()
        
        # Compute query embedding
        query_vector = self._compute_embedding(query)
        
        # Build filter
        where_clause = None
        if filter_dict:
            conditions = []
            for key, value in filter_dict.items():
                conditions.append(f"{key} = '{value}'")
            where_clause = " AND ".join(conditions)
        
        # Search with filter
        if where_clause:
            results = self.table.search(query_vector).where(where_clause).limit(top_k).to_list()
        else:
            results = self.table.search(query_vector).limit(top_k).to_list()
        
        logger.info(f"Hybrid search returned {len(results)} results")
        
        return results
    
    def _compute_embedding(self, text: str) -> List[float]:
        """
        Compute embedding for text
        
        In production, use sentence-transformers or OpenAI embeddings.
        For now, use simple hash-based embedding (placeholder).
        """
        # Placeholder: hash-based embedding (NOT semantic!)
        # In production: from sentence_transformers import SentenceTransformer
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # embedding = model.encode(text).tolist()
        
        # Simple hash-based placeholder
        hash_bytes = hashlib.md5(text.encode()).digest()
        # Expand to 384 dimensions (typical embedding size)
        embedding = list(hash_bytes) * 24  # 16 * 24 = 384
        embedding = embedding[:384]
        # Normalize to float
        embedding = [float(x) / 256.0 for x in embedding]
        
        return embedding
    
    def delete_document(self, doc_id: str):
        """Delete all LDUs for a document"""
        if self.table is None:
            self.connect()
        
        self.table.delete(f"doc_id = '{doc_id}'")
        logger.info(f"Deleted document: {doc_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if self.table is None:
            self.connect()
        
        count = self.table.count_rows()
        
        return {
            "total_ldus": count,
            "db_path": str(self.db_path),
            "table_name": "ldus"
        }


class InMemoryTable:
    """Fallback in-memory table when LanceDB is not available"""
    
    def __init__(self):
        self.records = []
    
    def add(self, records: List[Dict]):
        self.records.extend(records)
    
    def search(self, query_vector):
        return self
    
    def limit(self, top_k):
        return self
    
    def to_list(self):
        return self.records[:10]
    
    def count_rows(self):
        return len(self.records)
    
    def delete(self, condition):
        pass  # Simplified


# Singleton instance
_vector_store = None

def get_vector_store() -> VectorStore:
    """Get or create vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
        _vector_store.connect()
    return _vector_store