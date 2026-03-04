
"""
Phase 4: FactTable Extractor

Extracts key-value facts from financial/numerical documents into SQLite.
Enables precise SQL querying for numerical claims.
"""

import sqlite3
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from src.models.schemas import LogicalDocumentUnit


class FactTableExtractor:
    """
    Extract key-value facts into SQLite for precise querying
    
    Example facts:
    - revenue: $4.2B
    - fiscal_year: 2023
    - quarter: Q3
    - net_income: $1.5B
    """
    
    def __init__(self, db_path: str = ".refinery/facts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"FactTableExtractor initialized (db: {db_path})")
    
    def _init_db(self):
        """Create facts table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                fact_key TEXT NOT NULL,
                fact_value TEXT NOT NULL,
                fact_type TEXT,
                unit TEXT,
                page_number INTEGER,
                bounding_box TEXT,
                content_hash TEXT,
                source_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for fast querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_doc_id ON facts(doc_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fact_key ON facts(fact_key)
        """)
        
        conn.commit()
        conn.close()
        logger.debug("FactTable database initialized")
    
    def extract_facts(self, ldu: LogicalDocumentUnit) -> List[Dict[str, Any]]:
        """
        Extract facts from LDU using pattern matching
        
        Args:
            ldu: LogicalDocumentUnit with content
            
        Returns:
            List of extracted facts
        """
        facts = []
        content = ldu.content
        
        # Pattern 1: Key-value pairs (e.g., "Revenue: $4.2B")
        kv_pattern = r'([A-Za-z\s]+):\s*\$?([\d,.]+[BMK]?)'
        for match in re.finditer(kv_pattern, content, re.IGNORECASE):
            key = match.group(1).strip().lower().replace(' ', '_')
            value = match.group(2).strip()
            
            fact = {
                "doc_id": ldu.source_doc,
                "fact_key": key,
                "fact_value": value,
                "fact_type": self._classify_fact_type(key),
                "unit": self._extract_unit(value),
                "page_number": ldu.page_refs[0] if ldu.page_refs else 1,
                "bounding_box": str(ldu.bounding_box) if ldu.bounding_box else None,
                "content_hash": ldu.content_hash,
                "source_text": match.group(0)[:200]
            }
            facts.append(fact)
        
        # Pattern 2: Financial metrics (e.g., "total revenue of $50M")
        metric_pattern = r'(revenue|income|profit|assets|liabilities|equity)\s+(?:of\s+)?\$?([\d,.]+[BMK]?)'
        for match in re.finditer(metric_pattern, content, re.IGNORECASE):
            key = match.group(1).strip().lower()
            value = match.group(2).strip()
            
            fact = {
                "doc_id": ldu.source_doc,
                "fact_key": key,
                "fact_value": value,
                "fact_type": "financial_metric",
                "unit": self._extract_unit(value),
                "page_number": ldu.page_refs[0] if ldu.page_refs else 1,
                "bounding_box": str(ldu.bounding_box) if ldu.bounding_box else None,
                "content_hash": ldu.content_hash,
                "source_text": match.group(0)[:200]
            }
            facts.append(fact)
        
        # Pattern 3: Fiscal periods (e.g., "FY 2023", "Q3 2024")
        period_pattern = r'(FY|Fiscal\s+Year|Q[1-4])\s*(\d{4})'
        for match in re.finditer(period_pattern, content, re.IGNORECASE):
            key = f"{match.group(1).lower().replace(' ', '_')}_period"
            value = f"{match.group(1)} {match.group(2)}"
            
            fact = {
                "doc_id": ldu.source_doc,
                "fact_key": key,
                "fact_value": value,
                "fact_type": "fiscal_period",
                "unit": None,
                "page_number": ldu.page_refs[0] if ldu.page_refs else 1,
                "bounding_box": str(ldu.bounding_box) if ldu.bounding_box else None,
                "content_hash": ldu.content_hash,
                "source_text": match.group(0)[:200]
            }
            facts.append(fact)
        
        return facts
    
    def _classify_fact_type(self, key: str) -> str:
        """Classify fact type based on key"""
        key_lower = key.lower()
        
        if any(word in key_lower for word in ['revenue', 'income', 'profit']):
            return "revenue_metric"
        elif any(word in key_lower for word in ['asset', 'liability', 'equity']):
            return "balance_sheet_metric"
        elif any(word in key_lower for word in ['fiscal', 'year', 'quarter', 'q1', 'q2', 'q3', 'q4']):
            return "fiscal_period"
        elif any(word in key_lower for word in ['tax', 'expenditure']):
            return "tax_metric"
        else:
            return "general"
    
    def _extract_unit(self, value: str) -> Optional[str]:
        """Extract unit from value (e.g., $4.2B → B)"""
        if 'B' in value.upper():
            return "billions"
        elif 'M' in value.upper():
            return "millions"
        elif 'K' in value.upper():
            return "thousands"
        return None
    
    def insert_facts(self, facts: List[Dict[str, Any]]):
        """Insert facts into database"""
        if not facts:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for fact in facts:
            cursor.execute("""
                INSERT INTO facts (doc_id, fact_key, fact_value, fact_type, unit, 
                                   page_number, bounding_box, content_hash, source_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fact["doc_id"],
                fact["fact_key"],
                fact["fact_value"],
                fact["fact_type"],
                fact["unit"],
                fact["page_number"],
                fact["bounding_box"],
                fact["content_hash"],
                fact["source_text"]
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Inserted {len(facts)} facts into FactTable")
    
    def query_facts(self, key: str, doc_id: Optional[str] = None) -> List[Dict]:
        """
        Query facts by key
        
        Args:
            key: Fact key to search for
            doc_id: Optional document ID filter
            
        Returns:
            List of matching facts
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if doc_id:
            cursor.execute("""
                SELECT * FROM facts 
                WHERE fact_key = ? AND doc_id = ?
                ORDER BY created_at DESC
            """, (key, doc_id))
        else:
            cursor.execute("""
                SELECT * FROM facts 
                WHERE fact_key = ?
                ORDER BY created_at DESC
            """, (key,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    def get_all_facts(self, doc_id: str) -> List[Dict]:
        """Get all facts for a document"""
        return self.query_facts("%", doc_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get FactTable statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM facts")
        total_facts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT doc_id) FROM facts")
        total_docs = cursor.fetchone()[0]
        
        cursor.execute("SELECT fact_type, COUNT(*) FROM facts GROUP BY fact_type")
        by_type = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_facts": total_facts,
            "total_documents": total_docs,
            "by_type": by_type,
            "db_path": str(self.db_path)
        }