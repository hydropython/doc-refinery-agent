"""
Semantic Chunker with Spatial Provenance

Every LDU preserves:
- bounding_box (x0, y0, x1, y1) from pdfplumber
- page_number from source
- content_hash for audit trail
- table_structure (headers + rows) for tables

Unlike naive token-based chunking:
- Tables stay intact with headers and rows preserved
- Bounding boxes preserved from source
- Page numbers tracked per chunk
- Spatial proximity = semantic meaning
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib
import json
from loguru import logger

from src.models.schemas import LogicalDocumentUnit, ChunkType, BoundingBox


class SemanticChunker:
    """
    Structure-aware chunking that preserves spatial provenance
    
    Key Features:
    - Tables preserved with headers + rows (not flattened)
    - Bounding boxes from pdfplumber for every LDU
    - Page numbers tracked per chunk
    - Content hash for audit trail
    - Metadata for additional context
    - OCR content support for scanned PDFs
    """
    
    def __init__(self, max_tokens: int = 512, overlap: int = 50):
        self.max_tokens = max_tokens
        self.overlap = overlap
        logger.info(f"SemanticChunker initialized (max: {max_tokens}, overlap: {overlap})")
    
    def chunk_with_provenance(
        self, 
        extracted_content: str, 
        pdf_path: str,
        doc_id: str
    ) -> List[LogicalDocumentUnit]:
        """
        Chunk content while preserving spatial provenance
        
        For scanned PDFs: Use extracted_content from OCR
        For digital PDFs: Use pdfplumber extraction
        
        Args:
            extracted_content: Text from extraction (OCR or pdfplumber)
            pdf_path: Path to source PDF
            doc_id: Document identifier
            
        Returns:
            List[LogicalDocumentUnit] with bounding boxes, page refs, and table structure
        """
        import pdfplumber
        
        ldus = []
        
        # ========== PRIORITY 1: USE OCR-EXTRACTED CONTENT ==========
        # For scanned PDFs, extracted_content comes from OCR (Strategy B)
        if extracted_content and len(extracted_content.strip()) > 50:
            logger.info(f"Using OCR-extracted content ({len(extracted_content)} chars)")
            
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    if len(pdf.pages) > 0:
                        page = pdf.pages[0]
                        words = page.extract_words()
                        
                        # Calculate bounding box
                        if words:
                            x0 = min(w['x0'] for w in words)
                            y0 = min(w['top'] for w in words)
                            x1 = max(w['x1'] for w in words)
                            y1 = max(w['bottom'] for w in words)
                            bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
                        else:
                            # Full page bbox as fallback
                            bbox = BoundingBox(x0=0, y0=0, x1=page.width, y1=page.height)
                        
                        content_hash = hashlib.sha256(extracted_content[:500].encode()).hexdigest()[:16]
                        
                        ldu = LogicalDocumentUnit(
                            content=extracted_content,
                            chunk_type=ChunkType.TEXT,
                            page_refs=[1],  # Single page (OCR extracted page)
                            bounding_box=bbox,
                            parent_section="Page 1",
                            token_count=len(extracted_content.split()) // 4,
                            content_hash=content_hash,
                            source_doc=doc_id,
                            metadata={
                                "char_count": len(extracted_content),
                                "source": "ocr",
                                "bbox_source": "words"
                            }
                        )
                        ldus.append(ldu)
                        logger.info(f"Created 1 LDU from OCR content")
                        
            except Exception as e:
                logger.error(f"Error processing OCR content: {e}")
        
        # ========== PRIORITY 2: FALLBACK TO PDFPLUMBER ==========
        # For digital PDFs with embedded text
        if not ldus:
            logger.info(f"OCR content empty, trying pdfplumber extraction")
            
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    logger.info(f"Processing {len(pdf.pages)} pages for {doc_id}")
                    
                    for page_num, page in enumerate(pdf.pages, 1):
                        logger.debug(f"Processing page {page_num}")
                        
                        # ========== TEXT EXTRACTION WITH BBOX ==========
                        words = page.extract_words()
                        page_text = page.extract_text() or ""
                        
                        if len(page_text.strip()) > 50 and words:
                            # Calculate bounding box for page text
                            x0 = min(w['x0'] for w in words)
                            y0 = min(w['top'] for w in words)
                            x1 = max(w['x1'] for w in words)
                            y1 = max(w['bottom'] for w in words)
                            
                            bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
                            content_hash = hashlib.sha256(page_text[:500].encode()).hexdigest()[:16]
                            
                            ldu = LogicalDocumentUnit(
                                content=page_text[:500],
                                chunk_type=ChunkType.TEXT,
                                page_refs=[page_num],
                                bounding_box=bbox,
                                parent_section=f"Page {page_num}",
                                token_count=len(page_text.split()) // 4,
                                content_hash=content_hash,
                                source_doc=doc_id,
                                metadata={
                                    "word_count": len(words),
                                    "char_count": len(page_text),
                                    "bbox_source": "words"
                                }
                            )
                            ldus.append(ldu)
                            logger.debug(f"  Added TEXT LDU for page {page_num} ({len(page_text)} chars)")
                        
                        # ========== TABLE EXTRACTION WITH STRUCTURE ==========
                        tables = page.find_tables()
                        
                        for table_num, table in enumerate(tables):
                            table_data = table.extract()
                            
                            if table_data and len(table_data) >= 2:
                                structured_table = {
                                    "headers": table_data[0] if table_data[0] else [],
                                    "rows": table_data[1:] if len(table_data) > 1 else [],
                                    "num_columns": len(table_data[0]) if table_data[0] else 0,
                                    "num_rows": len(table_data) - 1 if len(table_data) > 1 else 0
                                }
                                
                                table_json = json.dumps(structured_table, ensure_ascii=False)
                                content_hash = hashlib.sha256(table_json.encode()).hexdigest()[:16]
                                
                                if hasattr(table, 'bbox') and table.bbox:
                                    bbox = BoundingBox(
                                        x0=table.bbox[0],
                                        y0=table.bbox[1],
                                        x1=table.bbox[2],
                                        y1=table.bbox[3]
                                    )
                                else:
                                    bbox = None
                                
                                ldu = LogicalDocumentUnit(
                                    content=table_json,
                                    chunk_type=ChunkType.TABLE,
                                    page_refs=[page_num],
                                    bounding_box=bbox,
                                    parent_section=f"Table {table_num + 1} - Page {page_num}",
                                    token_count=len(table_json.split()) // 4,
                                    content_hash=content_hash,
                                    source_doc=doc_id,
                                    metadata={
                                        "table_structure": True,
                                        "headers": structured_table["headers"],
                                        "num_columns": structured_table["num_columns"],
                                        "num_rows": structured_table["num_rows"],
                                        "bbox_source": "table"
                                    }
                                )
                                ldus.append(ldu)
                                logger.debug(
                                    f"  Added TABLE LDU for page {page_num}, table {table_num + 1} "
                                    f"({structured_table['num_rows']} rows x {structured_table['num_columns']} cols)"
                                )
                        
                        # ========== LIST EXTRACTION ==========
                        if page_text:
                            lines = page_text.split('\n')
                            list_items = []
                            list_bbox_words = []
                            
                            for line in lines:
                                stripped = line.strip()
                                if stripped.startswith(('•', '-', '*', '◦', '▪')) or stripped.startswith(tuple(f"{i}." for i in range(1, 100))):
                                    list_items.append(stripped)
                            
                            if len(list_items) >= 3:
                                list_text = json.dumps({"items": list_items, "type": "bullet_list"})
                                content_hash = hashlib.sha256(list_text.encode()).hexdigest()[:16]
                                
                                bbox = None
                                
                                ldu = LogicalDocumentUnit(
                                    content=list_text,
                                    chunk_type=ChunkType.LIST,
                                    page_refs=[page_num],
                                    bounding_box=bbox,
                                    parent_section=f"List - Page {page_num}",
                                    token_count=len(list_text.split()) // 4,
                                    content_hash=content_hash,
                                    source_doc=doc_id,
                                    metadata={
                                        "list_structure": True,
                                        "num_items": len(list_items),
                                        "bbox_source": "list_words"
                                    }
                                )
                                ldus.append(ldu)
                                logger.debug(f"  Added LIST LDU for page {page_num} ({len(list_items)} items)")
                        
                        # ========== HEADER EXTRACTION ==========
                        if page.chars:
                            chars_by_line = {}
                            for char in page.chars:
                                line_key = round(char.get('top', 0) / 10) * 10
                                if line_key not in chars_by_line:
                                    chars_by_line[line_key] = []
                                chars_by_line[line_key].append(char)
                            
                            for line_key, chars in chars_by_line.items():
                                if chars:
                                    avg_size = sum(c.get('size', 12) for c in chars) / len(chars)
                                    if avg_size > 14:
                                        header_text = ''.join(c.get('text', '') for c in chars).strip()
                                        if len(header_text) > 5 and len(header_text) < 200:
                                            x0 = min(c.get('x0', 0) for c in chars)
                                            y0 = min(c.get('top', 0) for c in chars)
                                            x1 = max(c.get('x1', 0) for c in chars)
                                            y1 = max(c.get('bottom', 0) for c in chars)
                                            
                                            bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
                                            content_hash = hashlib.sha256(header_text.encode()).hexdigest()[:16]
                                            
                                            ldu = LogicalDocumentUnit(
                                                content=header_text,
                                                chunk_type=ChunkType.HEADER,
                                                page_refs=[page_num],
                                                bounding_box=bbox,
                                                parent_section=f"Header - Page {page_num}",
                                                token_count=len(header_text.split()) // 4,
                                                content_hash=content_hash,
                                                source_doc=doc_id,
                                                metadata={
                                                    "header_structure": True,
                                                    "font_size": avg_size,
                                                    "bbox_source": "chars"
                                                }
                                            )
                                            ldus.append(ldu)
                                            logger.debug(f"  Added HEADER LDU for page {page_num} ({len(header_text)} chars)")
            
            except Exception as e:
                logger.error(f"Error chunking with provenance: {e}")
                import traceback
                traceback.print_exc()
                # Fallback: create simple LDUs without bbox
                ldus = self._fallback_chunk(extracted_content, doc_id)
        
        logger.info(f"Created {len(ldus)} LDUs with spatial provenance for {doc_id}")
        return ldus
    
    def _fallback_chunk(self, content: str, doc_id: str) -> List[LogicalDocumentUnit]:
        """Fallback chunking if pdfplumber fails"""
        ldus = []
        chunks = content.split('\n\n')[:10]
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) > 50:
                content_hash = hashlib.sha256(chunk.encode()).hexdigest()[:16]
                ldu = LogicalDocumentUnit(
                    content=chunk[:500],
                    chunk_type=ChunkType.TEXT,
                    page_refs=[i+1],
                    bounding_box=None,
                    parent_section="Section",
                    token_count=len(chunk.split()) // 4,
                    content_hash=content_hash,
                    source_doc=doc_id,
                    metadata={"fallback": True}
                )
                ldus.append(ldu)
        
        logger.warning(f"Fallback chunking created {len(ldus)} LDUs without bbox")
        return ldus
    
    def get_statistics(self, ldus: List[LogicalDocumentUnit]) -> Dict[str, Any]:
        """Get chunking statistics"""
        if not ldus:
            return {
                "total_ldus": 0,
                "total_tokens": 0,
                "by_type": {},
                "with_bbox": 0,
                "pages_covered": 0,
                "tables_with_structure": 0,
                "lists_with_structure": 0,
                "headers_with_structure": 0,
                "avg_tokens_per_ldu": 0
            }
        
        by_type = {}
        tables_with_structure = 0
        lists_with_structure = 0
        headers_with_structure = 0
        
        for ldu in ldus:
            chunk_type = str(ldu.chunk_type)
            by_type[chunk_type] = by_type.get(chunk_type, 0) + 1
            
            if ldu.metadata:
                if ldu.metadata.get("table_structure"):
                    tables_with_structure += 1
                if ldu.metadata.get("list_structure"):
                    lists_with_structure += 1
                if ldu.metadata.get("header_structure"):
                    headers_with_structure += 1
        
        return {
            "total_ldus": len(ldus),
            "total_tokens": sum(ldu.token_count for ldu in ldus),
            "by_type": by_type,
            "with_bbox": sum(1 for ldu in ldus if ldu.bounding_box),
            "pages_covered": len(set(page for ldu in ldus for page in ldu.page_refs)),
            "tables_with_structure": tables_with_structure,
            "lists_with_structure": lists_with_structure,
            "headers_with_structure": headers_with_structure,
            "avg_tokens_per_ldu": sum(ldu.token_count for ldu in ldus) / len(ldus) if ldus else 0
        }
    
    def export_ldus_to_json(self, ldus: List[LogicalDocumentUnit], output_path: str):
        """Export LDUs to JSON file for inspection"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        export_data = []
        for ldu in ldus:
            export_data.append({
                "content": ldu.content[:200],
                "chunk_type": str(ldu.chunk_type),
                "page_refs": ldu.page_refs,
                "bounding_box": ldu.bounding_box.to_list if ldu.bounding_box else None,
                "content_hash": ldu.content_hash,
                "source_doc": ldu.source_doc,
                "parent_section": ldu.parent_section,
                "token_count": ldu.token_count,
                "metadata": ldu.metadata
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(ldus)} LDUs to {output_file}")
        return output_file