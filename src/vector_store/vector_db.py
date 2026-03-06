"""
Vector Store: LanceDB Backend for LDU Embeddings

Stores LDUs with embeddings for semantic search.
Every LDU is embedded and stored with full provenance metadata.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger

from src.models.schemas import LogicalDocumentUnit


class VectorStore:
    """
    LanceDB vector store for LDU embeddings
    
    Schema:
    - id: Unique identifier
    - content: LDU text content
    - vector: Embedding (384-dimensional)
    - chunk_type: TEXT, TABLE, LIST, HEADER, etc.
    - page_refs: List of page numbers
    - bounding_box: JSON string of [x0, y0, x1, y1]
    - content_hash: SHA256 for audit trail
    - source_doc: Document ID
    - metadata: JSON with additional context
    """
    
    def __init__(self, db_path: str = ".refinery_db/lancedb"):
        self.db_path = Path(db_path)
        self.db = None
        self.table = None
        self.model = None
        logger.info(f"VectorStore initialized (path: {db_path})")
    
    def _load_embedding_model(self):
        """Load sentence transformer for embeddings"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.debug("Embedding model loaded: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not installed. Using mock embeddings.")
            self.model = None
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.model is None:
            self._load_embedding_model()
        
        if self.model:
            embedding = self.model.encode(text, convert_to_numpy=True).tolist()
            return embedding
        else:
            # Mock embedding (384 dimensions)
            import hashlib
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Expand to 384 dimensions
            embedding = list(hash_bytes) * 12  # 32 * 12 = 384
            return embedding[:384]
    
    def connect(self):
        """Connect to LanceDB with proper schema"""
        try:
            import lancedb
            import pyarrow as pa
            
            self.db = lancedb.connect(str(self.db_path))
            
            # Define proper schema with vector field
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), 384)),  # Required for LanceDB
                pa.field("chunk_type", pa.string()),
                pa.field("page_refs", pa.string()),  # Store as JSON string
                pa.field("bounding_box", pa.string()),  # Store as JSON string
                pa.field("content_hash", pa.string()),
                pa.field("source_doc", pa.string()),
                pa.field("metadata", pa.string())  # Store as JSON string
            ])
            
            try:
                self.table = self.db.open_table("ldus")
                logger.info(f"Opened existing table: ldus")
            except Exception:
                self.table = self.db.create_table("ldus", schema=schema)
                logger.info(f"Created new table: ldus")
            
            logger.info(f"Connected to LanceDB: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to connect to LanceDB: {e}")
            self.table = None
    
    def add_ldus(self, ldus: List[LogicalDocumentUnit]):
        """Add LDUs to vector store with embeddings"""
        if self.table is None:
            self.connect()
        
        if self.table is None:
            logger.error("Cannot add LDUs: table not available")
            return
        
        import json
        
        records = []
        for i, ldu in enumerate(ldus):
            # Generate embedding
            embedding = self._generate_embedding(ldu.content)
            
            # Create record
            record = {
                "id": f"{ldu.source_doc}_{i}_{ldu.content_hash}",
                "content": ldu.content[:8000],  # Truncate if too long
                "vector": embedding,
                "chunk_type": str(ldu.chunk_type),
                "page_refs": json.dumps(ldu.page_refs),
                "bounding_box": json.dumps(ldu.bounding_box.to_list) if ldu.bounding_box else "null",
                "content_hash": ldu.content_hash,
                "source_doc": ldu.source_doc,
                "metadata": json.dumps(ldu.metadata) if ldu.metadata else "{}"
            }
            records.append(record)
        
        # Add to table
        self.table.add(records)
        logger.info(f"Added {len(records)} LDUs to vector store")
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Semantic search for similar LDUs"""
        if self.table is None:
            self.connect()
        
        if self.table is None:
            return []
        
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Search
        results = self.table.search(query_embedding).limit(k).to_list()
        
        # Parse results
        parsed_results = []
        for r in results:
            parsed_results.append({
                "id": r["id"],
                "content": r["content"],
                "chunk_type": r["chunk_type"],
                "page_refs": json.loads(r["page_refs"]) if r["page_refs"] else [],
                "bounding_box": json.loads(r["bounding_box"]) if r["bounding_box"] else None,
                "content_hash": r["content_hash"],
                "source_doc": r["source_doc"],
                "score": r.get("_distance", 0.0)
            })
        
        return parsed_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        if self.table is None:
            self.connect()
        
        if self.table is None:
            return {"total_ldus": 0, "db_path": str(self.db_path)}
        
        try:
            # Count rows
            count = self.table.count_rows()
        except:
            count = 0
        
        return {
            "total_ldus": count,
            "db_path": str(self.db_path),
            "table_name": "ldus"
        }
    
    def clear(self):
        """Clear all data from vector store"""
        if self.table is None:
            self.connect()
        
        if self.table is None:
            return
        
        # Drop and recreate table
        self.db.drop_table("ldus")
        self.connect()
        logger.info("Vector store cleared")
    
    def close(self):
        """Close database connection"""
        self.db = None
        self.table = None
        logger.debug("Vector store connection closed")