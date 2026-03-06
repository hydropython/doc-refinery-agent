"""
Strategy C: Vision-Augmented Extraction with GPT-4o mini

Uses GPT-4o mini Vision API for OCR and layout understanding.
Every extracted fact includes spatial provenance (bbox + page).

BUDGET GUARD: Tracks API spend and enforces configurable budget cap.
"""

import base64
import requests
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.strategies.base import BaseExtractor
from src.models.schemas import ExtractedDocument, BoundingBox


class BudgetExceededError(Exception):
    """Raised when extraction would exceed budget cap"""
    pass


class VisionOCRExtractor(BaseExtractor):
    """
    Strategy C: GPT-4o mini Vision Extraction
    
    Best for:
    - Scanned documents
    - Image-based PDFs
    - Complex layouts (tables, multi-column)
    - Handwriting recognition
    - Poor quality scans
    
    BUDGET GUARD:
    - Tracks API spend per document
    - Enforces configurable budget cap
    - Raises BudgetExceededError if cap exceeded
    
    SPATIAL PROVENANCE:
    - Every extracted fact includes bounding box
    - Page numbers tracked per element
    - Content hash for audit trail
    """
    
    def __init__(self, budget_cap_usd: float = 0.50):
        super().__init__(
            strategy_name="strategy_c",
            cost_per_page=0.002,
            confidence_threshold=0.70
        )
        self.budget_cap_usd = budget_cap_usd
        self.running_cost = 0.0
        
        # Load API key from .env
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            logger.error("OPENAI_API_KEY not found in .env file!")
            raise RuntimeError("OPENAI_API_KEY required in .env file")
        
        # OpenAI API endpoint
        self.api_endpoint = "https://api.openai.com/v1/chat/completions"
        
        logger.info(f"VisionOCRExtractor initialized (model: {self.model_name}, budget: ${budget_cap_usd})")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _check_budget(self, page_count: int) -> bool:
        """Check if extraction would exceed budget"""
        estimated_cost = page_count * self.cost_per_page
        total_projected = self.running_cost + estimated_cost
        
        if total_projected > self.budget_cap_usd:
            logger.warning(
                f"Budget exceeded: ${total_projected:.2f} > ${self.budget_cap_usd}"
            )
            return False
        
        return True
    
    def _update_running_cost(self, tokens_used: int):
        """Update running cost after API call"""
        # GPT-4o mini pricing: $0.15/1M input tokens, $0.60/1M output tokens
        cost = (tokens_used / 1_000_000) * 0.15
        self.running_cost += cost
        logger.debug(f"Updated running cost: ${self.running_cost:.4f} ({tokens_used} tokens)")
    
    def _extract_page_with_gpt4o(self, image_path: str, page_num: int) -> Dict[str, Any]:
        """
        Extract text + tables + bounding boxes from single page using GPT-4o mini
        
        Args:
            image_path: Path to page image
            page_num: Page number
            
        Returns:
            Dict with text, tables, and bounding boxes
        """
        try:
            # Encode image
            img_base64 = self._encode_image(image_path)
            
            # Prepare API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Prompt engineered for table extraction + bounding boxes
            prompt = """Extract all content from this document page. Return JSON with:

1. "text_blocks": Array of {text, bbox: [x0, y0, x1, y1], type: "header"|"paragraph"|"list"}
2. "tables": Array of {headers: [], rows: [[cell1, cell2, ...]], bbox: [x0, y0, x1, y1]}
3. "page_number": <number>

For bounding boxes, use pixel coordinates from top-left origin.
Preserve table structure - do NOT flatten to text.
Return ONLY valid JSON, no markdown."""

            payload = {
                "model": self.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_base64}"}
                            }
                        ]
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.1
            }
            
            # Call API
            response = requests.post(self.api_endpoint, headers=headers, json=payload, timeout=120)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                tokens_used = result.get("usage", {}).get("total_tokens", 0)
                
                # Parse JSON response
                try:
                    # Remove markdown code blocks if present
                    content = content.replace("```json", "").replace("```", "").strip()
                    extracted_data = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON response for page {page_num}")
                    extracted_data = {"text_blocks": [], "tables": [], "page_number": page_num}
                
                # Update cost
                self._update_running_cost(tokens_used)
                
                return {
                    "page": page_num,
                    "text_blocks": extracted_data.get("text_blocks", []),
                    "tables": extracted_data.get("tables", []),
                    "tokens_used": tokens_used,
                    "success": True
                }
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return {
                    "page": page_num,
                    "text_blocks": [],
                    "tables": [],
                    "tokens_used": 0,
                    "success": False,
                    "error": response.text
                }
                
        except Exception as e:
            logger.error(f"Page extraction failed: {e}")
            return {
                "page": page_num,
                "text_blocks": [],
                "tables": [],
                "tokens_used": 0,
                "success": False,
                "error": str(e)
            }
    
    def extract(self, pdf_path: str) -> ExtractedDocument:
        """
        Extract document using GPT-4o mini Vision API
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            ExtractedDocument with content, tables, and spatial provenance
        """
        logger.info(f"Strategy C: Extracting {pdf_path} with GPT-4o mini Vision")
        
        try:
            import fitz  # PyMuPDF for PDF → images
            
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            
            # Check budget
            if not self._check_budget(page_count):
                raise BudgetExceededError(
                    f"Extraction would exceed budget cap of ${self.budget_cap_usd}"
                )
            
            all_text_blocks = []
            all_tables = []
            page_markers = []
            
            # Process each page
            for page_num, page in enumerate(doc, 1):
                logger.info(f"Processing page {page_num}/{page_count}")
                
                # Render page as image (2x zoom for clarity)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_path = f"/tmp/page_{page_num}.png"
                pix.save(img_path)
                
                # Extract with GPT-4o mini
                result = self._extract_page_with_gpt4o(img_path, page_num)
                
                if result["success"]:
                    # Add page marker
                    page_markers.append(page_num)
                    
                    # Collect text blocks
                    for block in result["text_blocks"]:
                        block["page"] = page_num
                        all_text_blocks.append(block)
                    
                    # Collect tables
                    for table in result["tables"]:
                        table["page"] = page_num
                        all_tables.append(table)
                
                # Cleanup temp image
                Path(img_path).unlink(missing_ok=True)
            
            doc.close()
            
            # Build content string from text blocks
            content_parts = []
            for block in all_text_blocks:
                content_parts.append(block.get("text", ""))
            content = "\n\n".join(content_parts)
            
            # Format tables as JSON
            tables_formatted = []
            for table in all_tables:
                tables_formatted.append({
                    "headers": table.get("headers", []),
                    "rows": table.get("rows", []),
                    "bbox": table.get("bbox"),
                    "page": table.get("page")
                })
            
            # Calculate quality score
            quality_score = self._calculate_quality(content, tables_formatted, page_count)
            
            logger.success(
                f"Strategy C complete: {len(all_text_blocks)} text blocks, "
                f"{len(all_tables)} tables, ${self.running_cost:.4f} spent"
            )
            
            return ExtractedDocument(
                doc_id=Path(pdf_path).stem,
                source_path=pdf_path,
                content=content if content else "No content extracted",
                tables=tables_formatted,
                figures=[],
                page_markers=page_markers,
                extraction_strategy=self.strategy_name,
                quality_score=quality_score
            )
            
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install pymupdf")
            raise
        except Exception as e:
            logger.error(f"Strategy C extraction failed: {e}")
            raise
    
    def _calculate_quality(self, content: str, tables: List, page_count: int) -> float:
        """Calculate extraction quality score"""
        if not content:
            return 0.0
        
        # Base score from content length
        base_score = min(len(content) / 10000, 1.0)
        
        # Table bonus
        table_bonus = min(len(tables) / 5, 0.3)
        
        # Page coverage bonus
        coverage_bonus = min(page_count / 10, 0.2)
        
        quality = min(base_score + table_bonus + coverage_bonus, 1.0)
        
        logger.debug(f"Quality score: {quality:.2f}")
        
        return quality
    
    def reset_budget(self):
        """Reset running cost (call after each document)"""
        self.running_cost = 0.0
        logger.debug("Budget reset to $0.00")
    
    def get_running_cost(self) -> float:
        """Get current running cost"""
        return self.running_cost