"""Document Analyzer Agent - Stage 0"""

from typing import Dict, Any
from pathlib import Path
from loguru import logger
import fitz
import json


class DocumentAnalyzer:
    """
    Stage 0: Document Analysis
    
    Analyzes PDF documents to determine:
    - Page count
    - Scanned vs digital pages
    - Image count
    - Table indicators
    """
    
    def __init__(self):
        logger.info("DocumentAnalyzer initialized")
    
    def analyze(self, pdf_path: str) -> Dict[str, Any]:
        """Analyze a PDF document"""
        logger.info(f"Analyzing document: {pdf_path}")
        
        pdf = fitz.open(pdf_path)
        
        result = {
            "path": pdf_path,
            "pages": len(pdf),
            "scanned": 0,
            "digital": 0,
            "mixed": 0,
            "total_images": 0,
            "total_drawings": 0
        }
        
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text()
            images = page.get_images(full=True)
            drawings = page.get_drawings()
            
            # Use page.rect for dimensions
            page_area = page.rect.width * page.rect.height if page.rect else 1
            char_density = len(text) / page_area if page_area > 0 else 0
            
            # Classify page type
            has_images = len(images) > 0
            has_text = len(text.strip()) > 50
            has_drawings = len(drawings) > 10
            
            if has_images and not has_text:
                result["scanned"] += 1
            elif has_text and not has_images:
                result["digital"] += 1
            else:
                result["mixed"] += 1
            
            result["total_images"] += len(images)
            result["total_drawings"] += len(drawings)
        
        pdf.close()
        
        logger.info(f"Analysis complete: {result['pages']} pages")
        
        return result
    
    def analyze_page(self, pdf_path: str, page_num: int) -> Dict[str, Any]:
        """Analyze a single page"""
        pdf = fitz.open(pdf_path)
        
        if page_num >= len(pdf):
            pdf.close()
            return {"error": f"Page {page_num} not found"}
        
        page = pdf[page_num]
        text = page.get_text()
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        
        # Use page.rect for dimensions
        page_area = page.rect.width * page.rect.height if page.rect else 1
        char_density = len(text) / page_area if page_area > 0 else 0
        
        # Classify
        has_images = len(images) > 0
        has_text = len(text.strip()) > 50
        
        if has_images and not has_text:
            page_type = "scanned"
        elif has_text and not has_images:
            page_type = "digital"
        else:
            page_type = "mixed"
        
        result = {
            "page": page_num + 1,
            "page_type": page_type,
            "text_chars": len(text),
            "char_density": round(char_density, 4),
            "images": len(images),
            "drawings": len(drawings),
            "width": page.rect.width,
            "height": page.rect.height
        }
        
        pdf.close()
        return result
    
    def save_report(self, analysis: Dict[str, Any], output_path: str):
        """
        Save analysis report to JSON file
        
        Args:
            analysis: Analysis results dictionary
            output_path: Path to save report
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"Analysis report saved to: {output_path}")
