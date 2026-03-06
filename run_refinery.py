#!/usr/bin/env python3
"""
🏭 DOCUMENT INTELLIGENCE REFINERY
Production-Ready CLI Tool with Simple Page Selection

Features:
- Step 1: Select Document (1-4 or All)
- Step 2: Select Pages (Use PDF page number you see in viewer)
- Step 3: Page Preview (Text, Scanned, Images, Tables)
- Document Analysis (Stage 0)
- Strategy C Disabled (Local Only - Cost Optimized)
- Full Spatial Provenance
- 100% Local Processing ($0.00 cost)

Usage:
    uv run python run_refinery.py                           # Interactive mode
    uv run python run_refinery.py --doc 1 --page 4          # Direct mode
    uv run python run_refinery.py --batch                   # All documents
"""

import sys
import json
import argparse
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# Silence third-party logs
import logging
logging.getLogger("RapidOCR").setLevel(logging.ERROR)
logging.getLogger("docling").setLevel(logging.ERROR)
logging.getLogger("pdfplumber").setLevel(logging.ERROR)

# Load environment variables
load_dotenv()

# Configure logger - ONLY show warnings and errors (clean output)
logger.remove()
logger.add(
    sys.stderr,
    level="WARNING",
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>"
)

# Import pipeline components
from src.agents.triage import TriageAgent
from src.strategies.router import ExtractionRouter
from src.chunker.semantic_chunker import SemanticChunker
from src.chunker.page_index import PageIndexBuilder
from src.vector_store.vector_db import VectorStore
from src.agents.query_agent import QueryAgent
from src.agents.fact_table import FactTable
from src.agents.document_analyzer import DocumentAnalyzer


# =============================================================================
# DOCUMENT CATALOG
# =============================================================================

DOCUMENT_CATALOG = {
    "1": {
        "name": "AUDIT (Scanned Legal - DBE)",
        "path": "data/Audit Report - 2023.pdf",
        "class": "AUDIT"
    },
    "2": {
        "name": "CBE (Annual Financial Report)",
        "path": "data/CBE ANNUAL REPORT 2023-24.pdf",
        "class": "CBE"
    },
    "3": {
        "name": "FTA (Performance Assessment)",
        "path": "data/fta_performance_survey_final_report_2022.pdf",
        "class": "FTA"
    },
    "4": {
        "name": "TAX (Expenditure Report)",
        "path": "data/tax_expenditure_ethiopia_2021_22.pdf",
        "class": "TAX"
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_pdf_page_count(pdf_path: str) -> int:
    """Get actual page count from PDF file using PyMuPDF"""
    try:
        if not Path(pdf_path).exists():
            logger.warning(f"❌ File does not exist: {pdf_path}")
            return 0
        
        with fitz.open(pdf_path) as pdf:
            return pdf.page_count
            
    except Exception as e:
        logger.warning(f"⚠️  Could not get page count for {pdf_path}: {e}")
        return 0


def update_catalog_with_page_counts():
    """Update document catalog with actual page counts"""
    for key, doc in DOCUMENT_CATALOG.items():
        pdf_path = doc['path']
        if Path(pdf_path).exists():
            doc['total_pages'] = get_pdf_page_count(pdf_path)
        else:
            doc['total_pages'] = 0
            logger.warning(f"❌ Document not found: {pdf_path}")
    
    return DOCUMENT_CATALOG


def extract_single_page_pdf(input_path: str, page_num: int, output_path: str) -> str:
    """Extract a single page from PDF to a new file"""
    try:
        pdf = fitz.open(input_path)
        new_pdf = fitz.open()
        new_pdf.insert_pdf(pdf, from_page=page_num-1, to_page=page_num-1)
        new_pdf.save(output_path)
        new_pdf.close()
        pdf.close()
        return output_path
    except Exception as e:
        logger.error(f"Failed to extract page: {e}")
        return input_path


def extract_page_range_pdf(input_path: str, page_range: List[int], output_path: str) -> str:
    """Extract multiple pages from PDF to a new file"""
    try:
        pdf = fitz.open(input_path)
        new_pdf = fitz.open()
        
        for page_num in page_range:
            new_pdf.insert_pdf(pdf, from_page=page_num-1, to_page=page_num-1)
        
        new_pdf.save(output_path)
        new_pdf.close()
        pdf.close()
        return output_path
    except Exception as e:
        logger.error(f"Failed to extract pages: {e}")
        return input_path


def analyze_single_page(pdf_path: str, page_num: int) -> Dict[str, Any]:
    """Analyze a single page and return detailed information"""
    try:
        import pdfplumber
        
        with pdfplumber.open(pdf_path) as pdf:
            if page_num < 1 or page_num > len(pdf.pages):
                return {"error": f"Page {page_num} out of range"}
            
            page = pdf.pages[page_num - 1]
            
            text = page.extract_text() or ""
            text_chars = len(text)
            images = page.images
            image_count = len(images)
            tables = page.find_tables()
            table_count = len(tables)
            page_area = page.width * page.height
            char_density = text_chars / max(page_area, 1)
            
            is_scanned = text_chars < 50 or char_density < 0.01
            
            if is_scanned:
                page_type = "🖼️  SCANNED (Image-based)"
            elif image_count > 0 and text_chars > 100:
                page_type = "🔀 MIXED (Text + Images)"
            else:
                page_type = "📝 DIGITAL (Native text)"
            
            if is_scanned:
                strategy = "Strategy B (Local OCR)"
            elif table_count > 2:
                strategy = "Strategy B (Layout-Aware)"
            else:
                strategy = "Strategy A (Fast Text)"
            
            return {
                "page_number": page_num,
                "text_chars": text_chars,
                "char_density": char_density,
                "is_scanned": is_scanned,
                "page_type": page_type,
                "image_count": image_count,
                "table_count": table_count,
                "recommended_strategy": strategy,
                "page_dimensions": f"{page.width:.1f} x {page.height:.1f} points"
            }
            
    except Exception as e:
        return {"error": str(e)}


def print_page_preview(pdf_path: str, page_num: int):
    """Print detailed preview of a single page"""
    
    print(f"\n{'='*80}")
    print(f"📄 PAGE {page_num} PREVIEW — {Path(pdf_path).stem}")
    print(f"{'='*80}\n")
    
    analysis = analyze_single_page(pdf_path, page_num)
    
    if "error" in analysis:
        print(f"   ❌ Error: {analysis['error']}")
        return
    
    print(f"   📊 CONTENT ANALYSIS:")
    print(f"   {'─'*80}")
    print(f"   Page Type:        {analysis['page_type']}")
    print(f"   Text Characters:  {analysis['text_chars']:,}")
    print(f"   Char Density:     {analysis['char_density']:.2f} chars/point²")
    print(f"   Images:           {analysis['image_count']}")
    print(f"   Tables:           {analysis['table_count']}")
    print(f"   Page Size:        {analysis['page_dimensions']}")
    print()
    
    print(f"   🎯 EXTRACTION RECOMMENDATION:")
    print(f"   {'─'*80}")
    print(f"   Recommended:      {analysis['recommended_strategy']}")
    print(f"   Cost:             $0.00 (Local processing)")
    print()
    
    if analysis['text_chars'] > 0:
        print(f"   📝 TEXT PREVIEW (First 300 chars):")
        print(f"   {'─'*80}")
        
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            page = pdf.pages[page_num - 1]
            text = page.extract_text() or ""
            
            print(f"   ┌" + "─"*78 + "┐")
            for line in text[:300].split('\n')[:8]:
                print(f"   │ {line[:76]}")
            if len(text) > 300:
                print(f"   │ ... ({analysis['text_chars'] - 300} more characters)")
            print(f"   └" + "─"*78 + "┘")
            print()
    
    print(f"{'='*80}\n")


# =============================================================================
# CLI CLASS
# =============================================================================

class RefineryCLI:
    """Production CLI for Document Intelligence Refinery"""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.results = []
        self.start_time = datetime.now()
        self.selected_pages: Optional[List[int]] = None
        
        self.doc_catalog = update_catalog_with_page_counts()
        
        self.output_dirs = {
            "pageindex": Path(".refinery/pageindex"),
            "results": Path(".refinery/results"),
            "debug": Path(".refinery/debug"),
            "examples": Path("examples"),
            "analysis": Path(".refinery/analysis")
        }
        
        for dir_path in self.output_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def print_banner(self):
        """Print application banner"""
        print("\n" + "="*80)
        print("🏭  DOCUMENT INTELLIGENCE REFINERY")
        print("   Unstructured PDFs → Structured, Queryable Knowledge")
        print("   💰 100% Local Processing | $0.00 Cost | 100% Privacy")
        print("="*80 + "\n")
    
    def select_document(self) -> Optional[Dict[str, Any]]:
        """STEP 1: Interactive document selection"""
        
        if self.args.doc and self.args.doc in self.doc_catalog:
            return self.doc_catalog[self.args.doc]
        
        print("📂 STEP 1: SELECT DOCUMENT")
        print("-"*80)
        print("   Choose which document(s) to process:\n")
        
        for key, doc in self.doc_catalog.items():
            status = "✅" if Path(doc['path']).exists() else "❌"
            print(f"   {status} [{key}] {doc['name']}")
            print(f"       Path: {doc['path']}")
            if doc['total_pages'] > 0:
                print(f"       Pages: {doc['total_pages']} (detected from PDF)")
            else:
                print(f"       Pages: UNKNOWN (file not found)")
            print()
        
        print(f"   [A] ALL documents (batch process)")
        print(f"   [Q] Quit\n")
        
        while True:
            choice = input("   Enter choice [1-4/A/Q]: ").strip().upper()
            
            if choice == "Q":
                return None
            elif choice == "A":
                return {"batch": True, "name": "ALL DOCUMENTS"}
            elif choice in self.doc_catalog:
                doc = self.doc_catalog[choice]
                if not Path(doc['path']).exists():
                    print(f"   ❌ File not found: {doc['path']}")
                    continue
                return doc
            
            print("   ❌ Invalid choice. Please enter 1-4, A, or Q.")
    
    def select_pages(self, doc: Dict[str, Any]) -> Optional[List[int]]:
        """STEP 2: Simple page selection using PDF page numbers"""
        
        if self.args.page:
            print_page_preview(doc['path'], self.args.page)
            return [self.args.page]
        
        if doc.get("batch"):
            print("\n   📄 Processing ALL pages for ALL documents\n")
            return None
        
        total_pages = doc.get("total_pages", 0)
        
        if total_pages == 0:
            print(f"\n   ⚠️  Could not detect page count. Processing all pages.\n")
            return None
        
        print("\n" + "="*80)
        print("📄 STEP 2: SELECT PAGES")
        print("-"*80)
        print(f"   Document: {doc['name']}")
        print(f"   Total Pages: {total_pages}")
        print()
        print(f"   📌 TIP: Use the page number shown in your PDF viewer.")
        print(f"      Example: If PDF shows '19' at bottom, enter '19'")
        print()
        print(f"   [A] ALL pages (1-{total_pages})")
        print(f"   [S] SPECIFIC page number (with preview)")
        print(f"   [R] PAGE RANGE (e.g., 1-5)")
        print(f"   [P] PREVIEW a page")
        print(f"   [B] BACK to document selection\n")
        
        while True:
            choice = input("   Enter choice [A/S/R/P/B]: ").strip().upper()
            
            if choice == "B":
                return None
            elif choice == "A":
                print(f"\n   ✅ Processing ALL pages (1-{total_pages})\n")
                return None
            elif choice == "S":
                try:
                    page_num = int(input(f"   Enter page number [1-{total_pages}]: ").strip())
                    if 1 <= page_num <= total_pages:
                        print_page_preview(doc['path'], page_num)
                        confirm = input(f"   Process page {page_num}? [Y/n]: ").strip().lower()
                        if confirm != 'n':
                            print(f"\n   ✅ Processing PAGE {page_num}\n")
                            return [page_num]
                    else:
                        print(f"   ❌ Page must be between 1 and {total_pages}")
                except ValueError:
                    print("   ❌ Please enter a valid number")
            elif choice == "R":
                try:
                    range_input = input(f"   Enter page range (e.g., 1-{total_pages}): ").strip()
                    if "-" in range_input:
                        start, end = map(int, range_input.split("-"))
                        if 1 <= start <= end <= total_pages:
                            pages = list(range(start, end + 1))
                            print(f"\n   Preview of page {start}:")
                            print_page_preview(doc['path'], start)
                            confirm = input(f"   Process pages {start}-{end} ({len(pages)} pages)? [Y/n]: ").strip().lower()
                            if confirm != 'n':
                                print(f"\n   ✅ Processing pages {start}-{end}\n")
                                return pages
                    else:
                        print("   ❌ Please use format: start-end (e.g., 1-5)")
                except ValueError:
                    print("   ❌ Please enter valid numbers")
            elif choice == "P":
                try:
                    page_num = int(input(f"   Enter page number to preview [1-{total_pages}]: ").strip())
                    if 1 <= page_num <= total_pages:
                        print_page_preview(doc['path'], page_num)
                except ValueError:
                    print("   ❌ Please enter a valid number")
            else:
                print("   ❌ Invalid choice. Please enter A, S, R, P, or B.")
        
        return None
    
    def select_document_page_flow(self) -> Optional[Dict[str, Any]]:
        """Combined document + page selection flow"""
        doc = self.select_document()
        if doc:
            self.selected_pages = self.select_pages(doc)
        return doc
    
    def configure_processing(self) -> Dict[str, Any]:
        """Configure processing options"""
        
        config = {
            "max_tokens": 512,
            "overlap": 50,
            "run_audit": self.args.audit,
            "export_format": self.args.export or "json",
            "verbose": self.args.verbose,
            "page_filter": self.args.page or (self.selected_pages[0] if self.selected_pages and len(self.selected_pages) == 1 else None),
            "pages_to_process": self.selected_pages,
            "analyze_only": self.args.analyze_only
        }
        
        if not self.args.batch and not self.args.doc:
            change = input("\n⚙️  Change chunking settings? [y/N]: ").strip().lower()
            
            if change == 'y':
                try:
                    config['max_tokens'] = int(input("   Max tokens per LDU [512]: ").strip() or "512")
                    config['overlap'] = int(input("   Overlap tokens [50]: ").strip() or "50")
                except ValueError:
                    logger.warning("Invalid input, using defaults")
        
        return config
    
    def run_document_analysis(self, pdf_path: str, doc_id: str, pages_to_process: Optional[List[int]] = None) -> Dict[str, Any]:
        """Run Stage 0: Document Analysis"""
        
        print("\n📊 STAGE 0: DOCUMENT ANALYSIS")
        print("-"*60)
        
        if pages_to_process:
            if len(pages_to_process) == 1:
                temp_pdf = self.output_dirs["debug"] / f"{doc_id}_analysis_page_{pages_to_process[0]}.pdf"
                analysis_pdf = extract_single_page_pdf(pdf_path, pages_to_process[0], str(temp_pdf))
                print(f"   📄 Analyzing: Page {pages_to_process[0]} only")
            else:
                temp_pdf = self.output_dirs["debug"] / f"{doc_id}_analysis_pages_{pages_to_process[0]}-{pages_to_process[-1]}.pdf"
                analysis_pdf = extract_page_range_pdf(pdf_path, pages_to_process, str(temp_pdf))
                print(f"   📄 Analyzing: Pages {pages_to_process[0]}-{pages_to_process[-1]}")
        else:
            analysis_pdf = pdf_path
            print(f"   📄 Analyzing: ALL pages")
        
        analyzer = DocumentAnalyzer()
        analysis = analyzer.analyze(analysis_pdf)
        
        analysis_file = self.output_dirs["analysis"] / f"{doc_id}_analysis.json"
        analyzer.save_report(analysis, analysis_file)
        
        print(f"   📄 Pages:        {analysis.total_pages}")
        print(f"   🖼️  Scanned:      {analysis.scanned_pages} ({analysis.scanned_pages/max(analysis.total_pages,1)*100:.0f}%)")
        print(f"   📝 Digital:      {analysis.digital_pages}")
        print(f"   🎯 Strategy:     {analysis.recommended_strategy}")
        
        return {
            "total_pages": analysis.total_pages,
            "scanned_pages": analysis.scanned_pages,
            "digital_pages": analysis.digital_pages,
            "total_tables": analysis.total_tables,
            "total_images": analysis.total_images,
            "layout_complexity": analysis.layout_complexity,
            "recommended_strategy": analysis.recommended_strategy,
            "estimated_cost_usd": 0.00,
            "estimated_time_seconds": analysis.estimated_time_seconds
        }
    
    def process_document(self, pdf_path: str, doc_class: str, config: Dict, pages_to_process: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
        """Run full pipeline on document"""
        
        results = {
            "document": pdf_path,
            "class": doc_class,
            "timestamp": datetime.now().isoformat(),
            "pages_processed": pages_to_process if pages_to_process else "all",
            "stages": {}
        }
        
        try:
            doc_id = Path(pdf_path).stem
            
            # ========== STAGE 0: DOCUMENT ANALYSIS ==========
            analysis_results = self.run_document_analysis(pdf_path, doc_id, pages_to_process)
            results["stages"]["analysis"] = analysis_results
            
            if config.get('analyze_only'):
                print("\n👋 Analysis complete. Pipeline skipped (--analyze-only flag).")
                return results
            
            if not self.args.batch:
                proceed = input("\n   Proceed with full pipeline? [Y/n]: ").strip().lower()
                if proceed == 'n':
                    print("\n👋 Pipeline skipped by user.")
                    return results
            
            # ========== CREATE SINGLE-PAGE PDF IF NEEDED ==========
            extraction_pdf = pdf_path
            if pages_to_process:
                if len(pages_to_process) == 1:
                    temp_pdf = self.output_dirs["debug"] / f"{doc_id}_page_{pages_to_process[0]}.pdf"
                    extraction_pdf = extract_single_page_pdf(pdf_path, pages_to_process[0], str(temp_pdf))
                elif len(pages_to_process) < len(analysis_results.get('total_pages', 999)):
                    temp_pdf = self.output_dirs["debug"] / f"{doc_id}_pages_{pages_to_process[0]}-{pages_to_process[-1]}.pdf"
                    extraction_pdf = extract_page_range_pdf(pdf_path, pages_to_process, str(temp_pdf))
            
            # ========== STAGE 1: TRIAGE ==========
            print("\n🔍 STAGE 1: TRIAGE")
            print("-"*60)
            
            triage = TriageAgent()
            profile = triage.analyze(extraction_pdf)
            
            results["stages"]["triage"] = {
                "doc_id": profile.doc_id,
                "origin_type": str(profile.origin_type),
                "layout": str(profile.layout_complexity),
                "recommended_strategy": profile.recommended_strategy,
                "confidence": profile.confidence_score,
                "pages": profile.page_count,
                "text_chars": profile.text_chars
            }
            
            print(f"   📋 Type:         {profile.origin_type.value}")
            print(f"   📐 Layout:       {profile.layout_complexity.value}")
            print(f"   🎯 Strategy:     {profile.recommended_strategy}")
            print(f"   ✅ Confidence:   {profile.confidence_score:.2f}")
            
            # ========== STAGE 2: EXTRACTION ==========
            print("\n📥 STAGE 2: EXTRACTION")
            print("-"*60)
            
            router = ExtractionRouter()
            extracted, strategy_used = router.extract(extraction_pdf, profile)
            
            results["stages"]["extraction"] = {
                "strategy": strategy_used,
                "quality_score": extracted.quality_score,
                "content_length": len(extracted.content),
                "tables": len(extracted.tables),
                "pages": len(extracted.page_markers)
            }
            
            print(f"   🔧 Strategy:     {strategy_used}")
            print(f"   📝 Content:      {len(extracted.content):,} chars")
            print(f"   ⭐ Quality:      {extracted.quality_score:.2f}")
            print(f"   💰 Cost:         $0.00 (100% local)")
            
            # ========== STAGE 3: CHUNKING ==========
            print("\n✂️  STAGE 3: SEMANTIC CHUNKING")
            print("-"*60)
            
            chunker = SemanticChunker(
                max_tokens=config['max_tokens'],
                overlap=config['overlap']
            )
            ldus = chunker.chunk_with_provenance(extracted.content, extraction_pdf, profile.doc_id)
            stats = chunker.get_statistics(ldus)
            
            results["stages"]["chunking"] = stats
            
            print(f"   📦 LDUs:         {stats['total_ldus']}")
            print(f"   📍 With BBox:    {stats['with_bbox']} ({stats['with_bbox']/max(stats['total_ldus'],1)*100:.0f}%)")
            print(f"   📄 Pages:        {stats['pages_covered']}")
            
            # ========== STAGE 4: PAGEINDEX ==========
            print("\n📑 STAGE 4: PAGEINDEX")
            print("-"*60)
            
            builder = PageIndexBuilder()
            page_index = builder.build(ldus, extraction_pdf, profile.page_count)
            
            results["stages"]["pageindex"] = {
                "sections": len(page_index.sections),
                "total_pages": page_index.total_pages,
                "total_ldus": page_index.total_ldus,
                "total_tokens": page_index.total_tokens
            }
            
            print(f"   📑 Sections:     {len(page_index.sections)}")
            print(f"   📄 Pages:        {page_index.total_pages}")
            print(f"   📦 LDUs:         {page_index.total_ldus}")
            
            # ========== STAGE 5: VECTOR STORE ==========
            print("\n🗄️  STAGE 5: VECTOR STORE")
            print("-"*60)
            
            vector_store = VectorStore()
            vector_store.connect()
            vector_store.add_ldus(ldus)
            vs_stats = vector_store.get_statistics()
            
            results["stages"]["vector_store"] = vs_stats
            
            print(f"   💾 Database:     LanceDB (local)")
            print(f"   📦 Total LDUs:   {vs_stats['total_ldus']}")
            
            # ========== STAGE 6: QUERY ==========
            print("\n❓ STAGE 6: QUERY INTERFACE")
            print("-"*60)
            
            query_agent = QueryAgent()
            query_agent.register_document(profile.doc_id, page_index, ldus)
            
            results["stages"]["query_agent"] = {
                "registered": True,
                "doc_id": profile.doc_id,
                "ldus": len(ldus)
            }
            
            print(f"   ✅ Status:       READY")
            print(f"   📦 Indexed:      {len(ldus)} LDUs")
            print()
            
            if not self.args.batch:
                sample_queries = {
                    "AUDIT": ["What is the audit opinion?", "What is the fiscal year?"],
                    "CBE": ["What is the total revenue?", "What is the net profit?"],
                    "FTA": ["What are the key findings?"],
                    "TAX": ["What is the total tax expenditure?"]
                }
                queries = sample_queries.get(doc_class, sample_queries.get("TAX", []))
                
                if queries:
                    print(f"   💬 Suggested:")
                    for i, q in enumerate(queries, 1):
                        print(f"      {i}. {q}")
                    print(f"      [SKIP] Continue without query\n")
                    
                    query_input = input(f"   Enter query (or number): ").strip()
                    
                    if query_input.upper() != "SKIP":
                        if query_input.isdigit() and 1 <= int(query_input) <= len(queries):
                            query_text = queries[int(query_input) - 1]
                        else:
                            query_text = query_input
                        
                        result = query_agent.query(query_text, doc_ids=[profile.doc_id])
                        
                        results["stages"]["query_result"] = {
                            "query": query_text,
                            "answer": result.answer[:200],
                            "confidence": result.confidence,
                            "sources": result.sources,
                            "pages": result.pages,
                            "provenance_count": len(result.provenance)
                        }
                        
                        print(f"\n   💬 Answer: {result.answer[:200]}...")
                        print(f"   📊 Confidence: {result.confidence:.2f}")
                        print(f"   📍 Provenance: {len(result.provenance)} chains")
            
            # ========== SAVE RESULTS ==========
            print("\n💾 SAVING RESULTS")
            print("-"*60)
            
            results_file = self.output_dirs["results"] / f"{doc_id}_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"   📁 Results: {results_file}")
            
            pageindex_file = self.output_dirs["pageindex"] / f"{doc_id}.json"
            pageindex_data = {
                "doc_id": page_index.doc_id,
                "source_path": page_index.source_path,
                "total_pages": page_index.total_pages,
                "sections": [
                    {
                        "title": s.title,
                        "page_start": s.page_start,
                        "page_end": s.page_end,
                        "summary": s.summary,
                        "ldu_count": s.ldu_count
                    }
                    for s in page_index.sections
                ],
                "total_ldus": page_index.total_ldus,
                "strategy_used": strategy_used,
                "quality_score": extracted.quality_score
            }
            
            with open(pageindex_file, 'w') as f:
                json.dump(pageindex_data, f, indent=2)
            print(f"   📁 PageIndex: {pageindex_file}")
            
            ldu_export = chunker.export_ldus_to_json(
                ldus,
                self.output_dirs["debug"] / f"{doc_id}_ldus.json"
            )
            print(f"   📁 LDUs: {ldu_export}")
            
            fact_table = FactTable()
            fact_table.connect()
            fact_table.close()
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            results["error"] = str(e)
            return results
    
    def print_client_deliverables(self, results: List[Dict[str, Any]]):
        """Print client-focused deliverables summary"""
        print("\n" + "="*80)
        print("📋 CLIENT DELIVERABLES")
        print("="*80)
        
        if results:
            result = results[0]
            stages = result.get('stages', {})
            
            print("\n✅ 1. SEARCHABLE DOCUMENTS")
            print(f"   Status: READY | Query your documents in natural language")
            
            print("\n✅ 2. EXTRACTED CONTENT")
            chars = stages.get('extraction', {}).get('content_length', 0)
            print(f"   Status: COMPLETE | {chars:,} characters extracted")
            print(f"   Location: .refinery/results/")
            
            print("\n✅ 3. SOURCE VERIFICATION")
            bbox = stages.get('chunking', {}).get('with_bbox', 0)
            print(f"   Status: ENABLED | {bbox} LDUs with page + location tracking")
            
            print("\n✅ 4. COST & PRIVACY")
            pages = stages.get('analysis', {}).get('total_pages', 1)
            savings = pages * 0.002
            print(f"   Cloud Cost: ${savings:.4f} | Your Cost: $0.00 | Savings: 100%")
            print(f"   Privacy: 100% local (no data leaves premises)")
        
        print("\n⚠️  KNOWN LIMITATIONS (Post-Interim Improvements)")
        print("-"*60)
        print("   • Charts/Graphs: Detected but not interpreted")
        print("   • Complex Tables: Basic extraction only")
        print("   • OCR Quality: 19-23% (word boundary improvements planned)")
        print()
        
        print("\n" + "="*80)
        print("✅ PROCESSING COMPLETE")
        print("="*80)
        
        elapsed = datetime.now() - self.start_time
        print(f"\n⏱️  Total Time: {elapsed}")
        print(f"📁 Output: .refinery/")
        print()
    
    def run(self):
        """Main execution"""
        self.print_banner()
        
        doc = self.select_document_page_flow()
        
        if not doc:
            print("\n👋 No document selected. Exiting.")
            return
        
        config = self.configure_processing()
        
        if doc.get("batch"):
            print("\n🔄 BATCH MODE: Processing all documents...\n")
            
            for key, doc_info in self.doc_catalog.items():
                print(f"\n{'='*80}")
                print(f"📄 Processing: {doc_info['name']}")
                print(f"{'='*80}")
                
                if not Path(doc_info['path']).exists():
                    logger.warning(f"File not found: {doc_info['path']}")
                    continue
                
                result = self.process_document(
                    pdf_path=doc_info['path'],
                    doc_class=doc_info['class'],
                    config=config,
                    pages_to_process=None
                )
                
                if result:
                    self.results.append(result)
        else:
            if not Path(doc['path']).exists():
                print(f"\n❌ File not found: {doc['path']}")
                return
            
            result = self.process_document(
                pdf_path=doc['path'],
                doc_class=doc['class'],
                config=config,
                pages_to_process=self.selected_pages
            )
            
            if result:
                self.results.append(result)
        
        self.print_client_deliverables(self.results)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="🏭 Document Intelligence Refinery CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interactive Mode:
  uv run python run_refinery.py              # Full interactive

Direct Mode:
  uv run python run_refinery.py --doc 1      # Process AUDIT
  uv run python run_refinery.py --doc 1 --page 4   # Page 4 only
  uv run python run_refinery.py --batch      # All documents
        """
    )
    
    parser.add_argument("--doc", "-d", type=str, choices=["1", "2", "3", "4"])
    parser.add_argument("--page", "-p", type=int, help="Specific page number")
    parser.add_argument("--batch", "-b", action="store_true")
    parser.add_argument("--audit", "-a", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--export", "-e", type=str, choices=["json", "csv", "markdown"], default="json")
    parser.add_argument("--verbose", "-v", action="store_true")
    
    args = parser.parse_args()
    
    cli = RefineryCLI(args)
    cli.run()


if __name__ == "__main__":
    main()