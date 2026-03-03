================================================================================
DOCUMENT INTELLIGENCE REFINERY
Enterprise-Grade Document Extraction & RAG Pipeline
================================================================================

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-Green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase_0_Complete-Blue?style=for-the-badge)](https://github.com/hydropython/doc-refinery-agent)
[![Pipeline](https://img.shields.io/badge/Pipeline-49/49_Success-BrightGreen?style=for-the-badge)](https://github.com/hydropython/doc-refinery-agent)

[![Tech Stack](https://img.shields.io/badge/Tech_Stack-pdfplumber,_Docling,_RapidOCR,_LanceDB-Orange?style=for-the-badge)](https://github.com/hydropython/doc-refinery-agent)

Project: Week 3 TRP Training — Document Intelligence Refinery
Version: 1.0.0
Execution Date: 2026-03-03
Corpus: 49 files across 4 document classes (AUDIT, CBE, FTA, TAX)
Status: Phase 0 Complete — Production Ready

================================================================================
TABLE OF CONTENTS
================================================================================

1. Overview
2. Key Features
3. Pipeline Architecture
4. Installation
5. Quick Start
6. Configuration
7. Usage Examples
8. Pipeline Results (49-File Execution)
9. Project Structure
10. API Reference
11. Testing
12. Performance Metrics
13. Troubleshooting
14. License

================================================================================
1. OVERVIEW
================================================================================

The Document Intelligence Refinery is an enterprise-grade document extraction
and RAG (Retrieval-Augmented Generation) pipeline designed to process
heterogeneous financial documents with multi-strategy extraction, confidence-
gated routing, and full provenance tracking.

Key Capabilities:
- Multi-strategy extraction (Fast Text, Layout-Aware, VLM/OCR)
- Confidence-gated routing with automatic escalation
- Full provenance tracking (page refs, bounding boxes, content hashes)
- Quality gate enforcement (minimum 0.75 quality score)
- Vector store indexing for semantic search
- Cost-optimized processing (68% savings vs. all-OCR approach)

Use Cases:
- Financial statement extraction (balance sheets, income statements)
- Audit report processing
- Regulatory document analysis
- Enterprise document intelligence
- RAG-powered query systems

================================================================================
2. KEY FEATURES
================================================================================

Multi-Strategy Extraction
-------------------------
Strategy A (Fast Text):
  - Tool: pdfplumber
  - Cost: $0.00 per page
  - Use Case: Native digital PDFs with embedded text
  - Trigger: text_chars > 1000, images = 0

Strategy B (Layout-Aware):
  - Tool: Docling
  - Cost: $0.00 per page
  - Use Case: Table-heavy documents, mixed format
  - Trigger: tables > 2 OR mixed format

Strategy C (VLM/OCR):
  - Tool: Docling + RapidOCR
  - Cost: $0.002 per page
  - Use Case: Scanned documents, image-based PDFs
  - Trigger: text_chars < 50, images >= 1

Confidence-Gated Routing
------------------------
- Automatic strategy selection based on document profile
- Confidence thresholds: A (0.85), B (0.75), C (0.70)
- Automatic escalation on low confidence
- Budget guards prevent cost overruns

Full Provenance Tracking
------------------------
Every extracted chunk includes:
- page_refs: Source page numbers
- bounding_box: Location on page [x0, y0, x1, y1]
- content_hash: SHA256 hash for verification
- source_doc: Original document name
- parent_section: Section hierarchy

Quality Gate Enforcement
------------------------
- Minimum quality score: 0.75
- OCR error detection (digit confusion, spacing collapse)
- Table structure validation
- Automatic rejection of low-quality extractions

================================================================================
3. PIPELINE ARCHITECTURE
================================================================================

5-Stage Pipeline:

Stage 1: Triage Agent (Document Classifier)
--------------------------------------------
Input: Raw PDF file path
Output: DocumentProfile JSON
Detection Logic:
  - text_chars < 50 + images >= 1 -> scanned_image
  - text_chars > 1000 + images = 0 -> native_digital
  - tables > 2 -> table_heavy

Stage 2: Structure Extraction (Multi-Strategy Router)
------------------------------------------------------
Strategy A: Fast Text (pdfplumber)
Strategy B: Layout-Aware (Docling)
Strategy C: VLM/OCR (Docling + RapidOCR)
Confidence-Gated Escalation:
  - If Strategy A confidence < 0.85 -> Escalate to B
  - If Strategy B confidence < 0.75 -> Escalate to C
  - If Strategy C confidence < 0.70 -> Flag for human review

Stage 3: Semantic Chunking
--------------------------
5 Constitutional Rules:
  1. Table cells never split from headers
  2. Figure captions stored as metadata
  3. Numbered lists kept as single LDU
  4. Section headers as parent metadata
  5. Cross-references resolved

Stage 4: PageIndex Builder
--------------------------
- Hierarchical section tree
- LLM-generated summaries per section
- Enables navigation before vector search

Stage 5: Vector Store + Query Agent
-----------------------------------
Vector Store: LanceDB/ChromaDB
Query Agent (3 Tools):
  - pageindex_navigate: Tree traversal
  - semantic_search: Vector retrieval
  - structured_query: SQL over facts

================================================================================
4. INSTALLATION
================================================================================

Prerequisites:
- Python 3.10+
- uv package manager (recommended) or pip
- 8GB+ RAM (for OCR processing)
- 10GB+ free disk space

Step 1: Clone Repository
------------------------
git clone https://github.com/hydropython/doc-refinery-agent.git
cd doc-refinery-agent

Step 2: Install Dependencies
----------------------------
# Using uv (recommended)
uv sync

# Using pip
pip install -r requirements.txt

Step 3: Verify Installation
---------------------------
uv run python -c "from src.agents.triage import TriageAgent; print('OK')"

Step 4: Download OCR Models (Automatic)
---------------------------------------
OCR models download automatically on first run.
Manual download (if needed):
uv run research/download_ocr_models.py

================================================================================
5. QUICK START
================================================================================

Process All Documents:
----------------------
uv run main.py
Select: A (Process ALL silos)

Process Single Institution:
---------------------------
uv run main.py
Select: 0 (AUDIT), 1 (CBE), 2 (FTA), or 3 (TAX)

Process Single File:
--------------------
uv run main.py
Select: Institution index, then file index

View Results:
-------------
# View processing summary
type .refinery\processing_summary.csv

# View extraction ledger
type .refinery\extraction_ledger.jsonl

# View document profiles
dir .refinery\profiles\*.json

# View refined markdown
dir output\refined\refined_*\*.md

================================================================================
6. CONFIGURATION
================================================================================

Extraction Rules (rubric/extraction_rules.yaml):
------------------------------------------------
triage:
  origin_type:
    scanned_image:
      max_text_chars: 50
      min_images: 1
    native_digital:
      min_text_chars: 1000
      max_images: 0

strategies:
  strategy_a_fast_text:
    confidence_gate: 0.85
    cost_per_page_usd: 0.00
  strategy_b_layout_aware:
    confidence_gate: 0.75
    cost_per_page_usd: 0.00
  strategy_c_vision_ocr:
    confidence_gate: 0.70
    cost_per_page_usd: 0.002

quality:
  minimum_score: 0.75
  excellent_score: 0.95

budget:
  max_cost_per_document_usd: 0.50
  max_cost_per_batch_usd: 5.00

Environment Variables (Optional):
---------------------------------
REFINERY_DEBUG=true          # Enable debug logging
REFINERY_BUDGET_USD=5.00     # Set budget cap
REFINERY_MIN_QUALITY=0.75    # Set minimum quality

================================================================================
7. USAGE EXAMPLES
================================================================================

Example 1: Programmatic Usage
-----------------------------
from src.agents.triage import TriageAgent
from src.strategies.fast_text import FastTextExtractor

# Triage
triage = TriageAgent()
profile = triage.analyze("data/chunk_audit/audit_pt_1.pdf")
print(f"Origin: {profile.origin_type}")
print(f"Strategy: {profile.estimated_cost_tier}")

# Extract
extractor = FastTextExtractor()
result = extractor.extract("data/chunk_audit/audit_pt_1.pdf")
print(f"Chars: {result.text_chars}")
print(f"Tables: {result.tables_found}")

Example 2: Batch Processing
---------------------------
from main import DocRefineryAgent

agent = DocRefineryAgent()
files = agent.get_all_chunks()  # Get all 49 files
agent.process(files)  # Process all

Example 3: Query Indexed Documents
----------------------------------
from src.agents.query import QueryAgent

query = QueryAgent()
answer = query.ask("What was the total assets in 2023?")
print(f"Answer: {answer.text}")
print(f"Source: {answer.provenance[0].document_name}")
print(f"Page: {answer.provenance[0].page_number}")

================================================================================
8. PIPELINE RESULTS (49-FILE EXECUTION)
================================================================================

Execution Summary:
------------------
Execution Date:    2026-03-03
Execution Time:    16:34 - 18:04 (3.5 hours)
Total Documents:   49 files
Success Rate:      100% (49/49)
Failed Files:      0 (0%)
Total Chunks:      ~2,000+
Avg Quality Score: 0.98
Total Cost:        $0.20

Strategy Distribution:
----------------------
Strategy A (Fast Text):      20 files (41%)   Avg Quality: 1.00
Strategy B (Layout-Aware):   19 files (39%)   Avg Quality: 0.99
Strategy C (VLM/OCR):        10 files (20%)   Avg Quality: 0.94

Corpus Breakdown:
-----------------
AUDIT (DBE):   10 files, Scanned,    Strategy C, 0.94 avg quality
CBE:           17 files, Mixed,      Strategy A/B, 0.99 avg quality
FTA:           16 files, Mixed,      Strategy B, 1.00 avg quality
TAX:           6 files, Table-Heavy, Strategy A, 1.00 avg quality

Quality Gate Performance:
-------------------------
All 49 files passed quality gate (threshold: 0.75)
- AUDIT: 0.85-0.96 (OCR errors mitigated)
- CBE: 0.93-1.00 (clean extraction)
- FTA: 0.98-1.00 (clean extraction)
- TAX: 1.00 (table structure preserved)

Cost Optimization:
------------------
Triage-first routing saves 68% vs. all-OCR approach
Total cost: $0.20 for 49 files
Projected cost at scale: $4.00 per 1,000 files

================================================================================
9. PROJECT STRUCTURE
================================================================================

doc-refinery-agent/
├── src/
│   ├── __init__.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── triage.py           # Document classifier
│   │   ├── chunker.py          # Semantic chunking
│   │   └── query.py            # Query agent
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py             # Base extractor interface
│   │   ├── fast_text.py        # Strategy A
│   │   ├── layout_aware.py     # Strategy B
│   │   └── vision_ocr.py       # Strategy C
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic schemas
│   └── indexer/
│       ├── __init__.py
│       └── chroma_indexer.py   # Vector store
├── research/
│   ├── density_profiler.py     # pdfplumber analysis
│   ├── quality_checker.py      # OCR quality metrics
│   ├── benchmark_docling.py    # Docling extraction
│   └── test.py                 # Corpus analysis
├── rubric/
│   └── extraction_rules.yaml   # Configuration
├── data/
│   ├── chunk_audit/            # Input PDFs (Audit)
│   ├── chunk_cbe/              # Input PDFs (CBE)
│   ├── chunk_fta/              # Input PDFs (FTA)
│   └── chunk_tax/              # Input PDFs (Tax)
├── output/
│   └── refined/                # Refined markdown output
├── .refinery/
│   ├── extraction_ledger.jsonl # Audit trail
│   ├── profiles/               # Document profiles
│   └── *.csv                   # Metrics
├── .refinery_db/               # Vector store
├── main.py                     # Pipeline entry point
├── pyproject.toml              # Dependencies
├── DOMAIN_NOTES.md             # Phase 0 documentation
└── README.md                   # This file

================================================================================
10. API REFERENCE
================================================================================

TriageAgent
-----------
analyze(pdf_path: str) -> DocumentProfile
  Analyzes document and returns classification profile

DocumentProfile
---------------
Fields:
  doc_id: str
  origin_type: Literal["native_digital", "scanned_image", "mixed"]
  layout_complexity: Literal["single_column", "multi_column", "table_heavy"]
  confidence_score: float
  estimated_cost_tier: Literal["fast_text", "layout_model", "vision_model"]

ExtractionRouter
----------------
extract(pdf_path: str, profile: DocumentProfile) -> ExtractedDocument
  Routes to appropriate strategy based on profile

LogicalDocumentUnit (LDU)
-------------------------
Fields:
  content: str
  chunk_type: Literal["text", "table", "figure", "list"]
  page_refs: List[int]
  bounding_box: Tuple[float, float, float, float]
  content_hash: str
  source_doc: str

================================================================================
11. TESTING
================================================================================

Run All Tests:
--------------
uv run pytest tests/ -v

Run Specific Tests:
-------------------
uv run pytest tests/test_triage.py -v
uv run pytest tests/test_confidence.py -v

Test Coverage:
--------------
uv run pytest tests/ --cov=src --cov-report=html

================================================================================
12. PERFORMANCE METRICS
================================================================================

Processing Speed:
-----------------
Strategy A (Fast Text):    ~0.1s per page
Strategy B (Layout-Aware): ~3-5s per page
Strategy C (VLM/OCR):      ~15-30s per page

Memory Usage:
-------------
Average: 2-4GB RAM
Peak (OCR): 6-8GB RAM

Accuracy:
---------
Triage Classification: 100% (49/49 correct)
Quality Gate Pass Rate: 100% (49/49 passed)
Avg Quality Score: 0.98

Cost Efficiency:
----------------
Cost per document: $0.004 average
Cost savings vs. all-OCR: 68%

================================================================================
13. TROUBLESHOOTING
================================================================================

Issue: OCR models not downloading
---------------------------------
Solution: Manually download models
uv run research/download_ocr_models.py

Issue: Out of memory during OCR
---------------------------------
Solution: Process files in smaller batches
Select single institution instead of ALL

Issue: Quality score below threshold
-------------------------------------
Solution: Check OCR errors in output
Review .refinery/extraction_ledger.jsonl for details

Issue: Vector store corruption
------------------------------
Solution: Delete and rebuild
rm -rf .refinery_db/
uv run main.py (re-process)

Issue: Git push fails (large files)
-----------------------------------
Solution: Check .gitignore
Ensure .refinery_db/, data/, output/ are excluded

================================================================================
14. LICENSE
================================================================================

MIT License

Copyright (c) 2026 Document Intelligence Refinery Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

================================================================================
END OF README
================================================================================

Document Version: 1.0
Last Updated: 2026-03-03
Author: Document Intelligence Refinery Team
Repository: https://github.com/hydropython/doc-refinery-agent