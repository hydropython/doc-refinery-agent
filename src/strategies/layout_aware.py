"""
Strategy B: Docling (TEXT ONLY) + RapidOCR (Amharic + BBox ONLY)
NO DUPLICATION - Clean extraction
"""

import fitz
import hashlib
from pathlib import Path
from typing import List, Optional
from loguru import logger
from src.models.schemas import ExtractedDocument, ProvenanceItem
from src.strategies.base import BaseExtractor

try:
    from docling.document_converter import DocumentConverter
    DOCLING_AVAILABLE = True
except:
    DOCLING_AVAILABLE = False

try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except:
    RAPIDOCR_AVAILABLE = False


def count_amharic_chars(text: str) -> int:
    amharic_ranges = [(0x1200, 0x137F), (0x1380, 0x139F), (0x2D80, 0x2DDF)]
    return sum(1 for c in text if any(s <= ord(c) <= e for s, e in amharic_ranges))


class LayoutAwareExtractor(BaseExtractor):
    def __init__(self, confidence_threshold: float = 0.75):
        super().__init__("strategy_b", 0.00, confidence_threshold)
        self.converter = DocumentConverter() if DOCLING_AVAILABLE else None
        self.ocr = RapidOCR() if RAPIDOCR_AVAILABLE else None
        logger.info(f"Strategy B: Docling={DOCLING_AVAILABLE}, RapidOCR={RAPIDOCR_AVAILABLE}")
    
    def extract(self, pdf_path: str, page_range: Optional[List[int]] = None) -> ExtractedDocument:
        logger.info("=" * 70)
        logger.info("  STRATEGY B: Docling (Text) + RapidOCR (Amharic+BBox)")
        logger.info("=" * 70)
        
        # ========== STEP 1: DOCLING (TEXT + TABLES - PRIMARY) ==========
        docling_text = ""
        docling_tables = []
        
        if self.converter:
            logger.info("  [1/3] Docling: Primary text + tables...")
            try:
                result = self.converter.convert(pdf_path)
                docling_text = result.document.export_to_text()
                
                for i, table in enumerate(result.document.tables, 1):
                    try:
                        df = table.export_to_dataframe()
                        docling_tables.append({
                            "table_id": i,
                            "page": 1,
                            "rows": df.values.tolist(),
                            "headers": list(df.columns),
                            "num_rows": len(df),
                            "num_cols": len(df.columns)
                        })
                    except Exception as e:
                        logger.warning(f"    Table {i} export failed: {e}")
                
                logger.info(f"   Docling: {len(docling_text):,} chars, {len(docling_tables)} tables")
            except Exception as e:
                logger.error(f"   Docling failed: {e}")
        
        # ========== STEP 2: RAPIDOCR (AMHARIC + BBOX ONLY - NO TEXT DUPLICATION) ==========
        amharic_supplement = ""
        ocr_images = []
        total_amharic = 0
        line_provenance = []
        
        if self.ocr:
            logger.info("  [2/3] RapidOCR: Amharic + BBox ONLY (no text duplication)...")
            try:
                pdf = fitz.open(pdf_path)
                pages_to_process = range(min(11, len(pdf)))
                
                for page_num in pages_to_process:
                    page = pdf[page_num]
                    actual_page = page_num + 1
                    
                    # Convert to image
                    mat = fitz.Matrix(2.0, 2.0)
                    pix = page.get_pixmap(matrix=mat)
                    
                    img_path = Path(f".refinery/ocr_page_{actual_page}.png")
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    pix.save(str(img_path))
                    
                    # Run OCR
                    ocr_result, _ = self.ocr(str(img_path))
                    
                    if ocr_result:
                        page_amharic = ""
                        line_num = 0
                        
                        for line in ocr_result:
                            line_text = line[1]
                            bbox_raw = line[0] if len(line) > 0 else [[0, 0], [100, 20]]
                            confidence = line[2] if len(line) > 2 else 0.9
                            
                            # Fix bbox format
                            try:
                                if isinstance(bbox_raw, (list, tuple)) and len(bbox_raw) == 2:
                                    if isinstance(bbox_raw[0], (list, tuple)) and len(bbox_raw[0]) >= 2:
                                        bbox = [float(bbox_raw[0][0]), float(bbox_raw[0][1]), 
                                                float(bbox_raw[1][0]), float(bbox_raw[1][1])]
                                    else:
                                        bbox = [0.0, 0.0, 100.0, 20.0]
                                else:
                                    bbox = [0.0, 0.0, 100.0, 20.0]
                            except:
                                bbox = [0.0, 0.0, 100.0, 20.0]
                            
                            if confidence > 0.5 and line_text.strip():
                                line_num += 1
                                
                                # ONLY extract Amharic (NOT all text - avoids duplication)
                                line_amharic_count = count_amharic_chars(line_text)
                                if line_amharic_count > 0:
                                    page_amharic += line_text + "\n"
                                    total_amharic += line_amharic_count
                                
                                # Track provenance for Amharic lines
                                if line_amharic_count > 0:
                                    line_provenance.append({
                                        "page": actual_page,
                                        "line": line_num,
                                        "bbox": bbox,
                                        "content_hash": hashlib.sha256(line_text.encode()).hexdigest()[:16],
                                        "source": "rapidocr",
                                        "char_count": len(line_text),
                                        "amharic_chars": line_amharic_count
                                    })
                        
                        # Save Amharic supplement only
                        if page_amharic.strip():
                            amharic_supplement += f"\n--- Page {actual_page} (Amharic) ---\n{page_amharic}\n"
                        
                        # Track image only if page has actual images
                        images_on_page = len(page.get_images())
                        if images_on_page > 0:
                            ocr_images.append({
                                "page": actual_page,
                                "image_path": str(img_path),
                                "ocr_text": page_amharic.strip(),
                                "amharic_chars": count_amharic_chars(page_amharic),
                                "lines": line_num,
                                "actual_images": images_on_page
                            })
                
                pdf.close()
                logger.info(f"   RapidOCR: {len(amharic_supplement):,} Amharic chars, {len(ocr_images)} images with OCR")
            except Exception as e:
                logger.error(f"   RapidOCR failed: {e}")
        
        # ========== STEP 3: MERGE (Docling Text + Amharic Supplement ONLY) ==========
        logger.info("  [3/3] Merging (Docling Text + Amharic Supplement)...")
        
        # Use Docling text as base (NO full OCR text - avoids duplication)
        final_text = docling_text
        
        # ONLY add Amharic supplement
        if amharic_supplement.strip():
            final_text += "\n\n=== AMHARIC SUPPLEMENT (from RapidOCR) ===\n" + amharic_supplement
        
        # Add tables from Docling
        all_tables = docling_tables
        
        if all_tables:
            final_text += "\n\n=== TABLES (from Docling) ===\n\n"
            for table in all_tables:
                final_text += f"Table {table.get('table_id')} (Page {table.get('page')}):\n"
                final_text += f"  Headers: {table.get('headers', [])}\n"
                for row in table.get('rows', [])[:10]:
                    final_text += f"  {row}\n"
                final_text += "\n"
        
        # Count actual images from PDF (not OCR pages)
        actual_image_count = 0
        try:
            pdf = fitz.open(pdf_path)
            for page_num in range(min(11, len(pdf))):
                page = pdf[page_num]
                actual_image_count += len(page.get_images())
            pdf.close()
        except:
            actual_image_count = len(ocr_images)
        
        logger.info(f"   MERGED: {len(final_text):,} chars (Docling + Amharic ONLY)")
        logger.info(f"   Tables: {len(all_tables)} (from Docling)")
        logger.info(f"   Images: {actual_image_count} (actual PDF images)")
        logger.info(f"   Amharic: {total_amharic:,} chars (from RapidOCR)")
        logger.info(f"   Line Provenance: {len(line_provenance)} entries")
        logger.info("=" * 70)
        
        # Create provenance chain
        provenance_chain = []
        for i in range(1, 12):
            page_lines = [p for p in line_provenance if p.get('page') == i]
            provenance_chain.append(ProvenanceItem(
                page=i,
                content_hash=hashlib.sha256(f"page_{i}".encode()).hexdigest()[:16],
                source_type="merged",
                char_count=sum(p.get('char_count', 0) for p in page_lines)
            ))
        
        return ExtractedDocument(
            doc_id=Path(pdf_path).stem,
            content=final_text,
            source_path=pdf_path,
            page_markers=list(range(1, 12)),
            quality_score=min(1.0, len(final_text) / 25000),
            extraction_strategy="docling_primary_rapidocr_supplement",
            provenance_chain=provenance_chain,
            metadata={
                "docling_chars": len(docling_text),
                "docling_tables": len(docling_tables),
                "tables": all_tables,
                "tables_count": len(all_tables),
                "images": ocr_images,
                "images_count": actual_image_count,
                "amharic_chars": total_amharic,
                "total_chars": len(final_text),
                "total_lines": len(line_provenance),
                "line_provenance": line_provenance,
                "merged": True,
                "no_duplication": True,
                "docling_text_only": True
            }
        )
