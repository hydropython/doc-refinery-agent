import pdfplumber
from loguru import logger
from src.models.schemas import DocumentProfile

def analyze_document(pdf_path: str) -> DocumentProfile:
    logger.info(f"Starting triage for: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        sample_pages = pdf.pages[:3]  # Speed over exhaustive search
        total_chars = 0
        v_lines = 0
        
        for page in sample_pages:
            total_chars += len(page.extract_text() or "")
            # Detect vertical lines as a proxy for columns/tables
            v_lines += len(page.edges) 
            
        avg_chars = total_chars / len(sample_pages)
        avg_lines = v_lines / len(sample_pages)
        
        # Origin Detection
        origin = "native_digital" if avg_chars > 100 else "scanned_image"
        
        # Complexity Detection
        if avg_lines > 10:
            complexity = "table_heavy"
        elif avg_lines > 5:
            complexity = "multi_column"
        else:
            complexity = "single_column"
            
        profile = DocumentProfile(
            doc_id=pdf_path.split("\\")[-1],
            origin_type=origin,
            layout_complexity=complexity,
            estimated_cost_tier="fast_text" if origin == "native_digital" else "vision_model",
            metadata={"avg_chars": avg_chars, "line_density": avg_lines}
        )
        
        logger.success(f"Triage Complete: {origin} | {complexity}")
        return profile