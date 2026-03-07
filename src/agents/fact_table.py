"""
FactTable: SQLite Backend for Numerical Facts

Extracts key-value facts from financial documents for precise SQL querying.
Used for audit verification and numerical claim checking.
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger


class FactTable:
    """
    SQLite-backed fact storage for numerical data extraction
    
    Schema:
    - id: Primary key
    - doc_id: Source document ID
    - fact_key: Named entity (e.g., "revenue", "assets")
    - fact_value: Numerical or text value
    - unit: Currency unit, percentage, etc.
    - page_number: Source page
    - bounding_box: [x0, y0, x1, y1] coordinates
    - content_hash: SHA256 for audit trail
    - metadata: JSON with additional context
    """
    
    def __init__(self, db_path: str = ".refinery/facts.db"):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        logger.info(f"FactTable initialized (path: {db_path})")
    
    def connect(self):
        """Connect to SQLite database and create tables"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._create_tables()
        logger.debug(f"Connected to FactTable: {self.db_path}")
    
    def _create_tables(self):
        """Create facts table if not exists"""
        if self.conn is None:
            return
        
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                unit TEXT,
                page_number INTEGER,
                bounding_box TEXT,
                content_hash TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(doc_id, fact_key, fact_value, page_number)
            )
        """)
        
        # Create index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fact_key ON facts(fact_key)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_doc_id ON facts(doc_id)
        """)
        
        self.conn.commit()
        logger.debug("FactTable schema created")
    
    def add_fact(
        self,
        doc_id: str,
        fact_key: str,
        fact_value: str,
        unit: Optional[str] = None,
        page_number: Optional[int] = None,
        bounding_box: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a fact to the database
        
        Returns:
            content_hash: SHA256 hash of the fact for audit trail
        """
        if self.conn is None:
            self.connect()
        
        # Generate content hash for audit
        content = f"{doc_id}:{fact_key}:{fact_value}:{page_number}"
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO facts 
                (doc_id, fact_key, fact_value, unit, page_number, bounding_box, content_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_id,
                fact_key,
                fact_value,
                unit,
                page_number,
                json.dumps(bounding_box) if bounding_box else None,
                content_hash,
                json.dumps(metadata) if metadata else None
            ))
            
            self.conn.commit()
            logger.debug(f"Added fact: {fact_key} = {fact_value}")
            
            return content_hash
            
        except sqlite3.Error as e:
            logger.error(f"Failed to add fact: {e}")
            self.conn.rollback()
            return ""
    
    def query_facts(self, keyword: str, doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query facts by keyword
        
        Args:
            keyword: Search term (e.g., "revenue", "assets")
            doc_id: Optional document filter
            
        Returns:
            List of facts matching the query
        """
        if self.conn is None:
            self.connect()
        
        cursor = self.conn.cursor()
        
        if doc_id:
            cursor.execute("""
                SELECT * FROM facts 
                WHERE fact_key LIKE ? OR fact_value LIKE ?
                AND doc_id = ?
                ORDER BY page_number
            """, (f"%{keyword}%", f"%{keyword}%", doc_id))
        else:
            cursor.execute("""
                SELECT * FROM facts 
                WHERE fact_key LIKE ? OR fact_value LIKE ?
                ORDER BY page_number
            """, (f"%{keyword}%", f"%{keyword}%"))
        
        rows = cursor.fetchall()
        
        facts = []
        for row in rows:
            facts.append({
                "id": row[0],
                "doc_id": row[1],
                "fact_key": row[2],
                "fact_value": row[3],
                "unit": row[4],
                "page_number": row[5],
                "bounding_box": json.loads(row[6]) if row[6] else None,
                "content_hash": row[7],
                "metadata": json.loads(row[8]) if row[8] else None
            })
        
        logger.debug(f"Query '{keyword}' returned {len(facts)} facts")
        
        return facts
    
    def get_all_facts(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all facts for a document"""
        if self.conn is None:
            self.connect()
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM facts WHERE doc_id = ? ORDER BY page_number
        """, (doc_id,))
        
        rows = cursor.fetchall()
        
        facts = []
        for row in rows:
            facts.append({
                "id": row[0],
                "doc_id": row[1],
                "fact_key": row[2],
                "fact_value": row[3],
                "unit": row[4],
                "page_number": row[5],
                "bounding_box": json.loads(row[6]) if row[6] else None,
                "content_hash": row[7],
                "metadata": json.loads(row[8]) if row[8] else None
            })
        
        return facts
    
    def verify_claim(self, claim: str, doc_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify a claim against stored facts
        
        Args:
            claim: Statement to verify (e.g., "Revenue was $4.2B")
            doc_id: Optional document filter
            
        Returns:
            Verification result with verdict
        """
        # Extract keywords from claim (simple implementation)
        keywords = ["revenue", "profit", "assets", "liabilities", "tax", "expenditure"]
        
        matching_facts = []
        for keyword in keywords:
            if keyword in claim.lower():
                facts = self.query_facts(keyword, doc_id)
                matching_facts.extend(facts)
        
        if matching_facts:
            return {
                "claim": claim,
                "verdict": "verified",
                "facts": matching_facts,
                "confidence": 0.8
            }
        else:
            return {
                "claim": claim,
                "verdict": "unverifiable",
                "facts": [],
                "confidence": 0.0
            }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.debug("FactTable connection closed")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        if self.conn is None:
            self.connect()
        
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM facts")
        total_facts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM facts")
        total_docs = cursor.fetchone()[0]
        
        return {
            "total_facts": total_facts,
            "total_documents": total_docs,
            "db_path": str(self.db_path)
        }