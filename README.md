# Document Intelligence Refinery

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-Green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase_0_Complete-Blue?style=for-the-badge)](https://github.com/hydropython/doc-refinery-agent)
[![Pipeline](https://img.shields.io/badge/Pipeline-49/49_Success-BrightGreen?style=for-the-badge)](https://github.com/hydropython/doc-refinery-agent)

**Enterprise-Grade Document Extraction & RAG Pipeline**

| Metric | Value |
|--------|-------|
| Version | 1.0.0 |
| Execution Date | 2026-03-03 |
| Corpus | 49 files (AUDIT, CBE, FTA, TAX) |
| Success Rate | 100% (49/49) |
| Avg Quality Score | 0.98 |
| Total Cost | $0.20 |

---

## Overview

The Document Intelligence Refinery is an enterprise-grade document extraction and RAG pipeline designed to process heterogeneous financial documents with multi-strategy extraction, confidence-gated routing, and full provenance tracking.

### Key Capabilities

- **Multi-strategy extraction** (Fast Text, Layout-Aware, VLM/OCR)
- **Confidence-gated routing** with automatic escalation
- **Full provenance tracking** (page refs, bounding boxes, content hashes)
- **Quality gate enforcement** (minimum 0.75 quality score)
- **Vector store indexing** for semantic search
- **Cost-optimized processing** (68% savings vs. all-OCR)

### Use Cases

- Financial statement extraction (balance sheets, income statements)
- Audit report processing
- Regulatory document analysis
- Enterprise document intelligence
- RAG-powered query systems

---

## Key Features

### Multi-Strategy Extraction

| Strategy | Tool | Cost/Page | Use Case | Trigger |
|----------|------|-----------|----------|---------|
| **A: Fast Text** | pdfplumber | $0.00 | Native digital PDFs | text_chars > 1000 |
| **B: Layout-Aware** | Docling | $0.00 | Table-heavy documents | tables > 2 |
| **C: VLM/OCR** | Docling + RapidOCR | $0.002 | Scanned documents | text_chars < 50 |

### Confidence-Gated Routing

- Automatic strategy selection based on document profile
- Confidence thresholds: A (0.85), B (0.75), C (0.70)
- Automatic escalation on low confidence
- Budget guards prevent cost overruns

### Full Provenance Tracking

Every extracted chunk includes:
- `page_refs`: Source page numbers
- `bounding_box`: Location on page [x0, y0, x1, y1]
- `content_hash`: SHA256 hash for verification
- `source_doc`: Original document name

---

## Pipeline Architecture

### 5-Stage Pipeline
Stage 1: Triage Agent (Document Classifier)
↓
Stage 2: Structure Extraction (Multi-Strategy Router)
↓
Stage 3: Semantic Chunking
↓
Stage 4: PageIndex Builder
↓
Stage 5: Vector Store + Query Agent


### Stage Details

**Stage 1: Triage Agent**
- Classifies: scanned_image, native_digital, mixed
- Uses pdfplumber for character density analysis

**Stage 2: Structure Extraction**
- Strategy A: Fast Text (pdfplumber)
- Strategy B: Layout-Aware (Docling)
- Strategy C: VLM/OCR (Docling + RapidOCR)

**Stage 3: Semantic Chunking**
- 5 constitutional rules enforced
- Tables never split from headers
- Every chunk gets page_refs, bounding_box, content_hash

**Stage 4: PageIndex Builder**
- Hierarchical section tree
- LLM-generated summaries per section

**Stage 5: Vector Store + Query Agent**
- LanceDB/ChromaDB for embeddings
- 3 tools: pageindex_navigate, semantic_search, structured_query

---

## Installation

### Prerequisites

- Python 3.10+
- uv package manager (recommended) or pip
- 8GB+ RAM (for OCR processing)
- 10GB+ free disk space

### Step 1: Clone Repository

```bash
git clone https://github.com/hydropython/doc-refinery-agent.git
cd doc-refinery-agent
```

### Install Dependencies
```bash
# Using uv (recommended)
uv sync

# Using pip
pip install -r requirements.txt
```

### Verify Installation
```bash
uv run python -c "from src.agents.triage import TriageAgent; print('OK')"
```

## Step 4: Download OCR Models
OCR models download automatically on first run.

## Process All Documents
```bash
uv run main.py
# Select: A (Process ALL silos)
```
## Process Single Institution
```bash
uv run main.py
# Select: 0 (AUDIT), 1 (CBE), 2 (FTA), or 3 (TAX)
```
## View Results
```bash
# View processing summary
type .refinery\processing_summary.csv

# View extraction ledger
type .refinery\extraction_ledger.jsonl

# View document profiles
dir .refinery\profiles\*.json
```

# Configuration
## Extraction Rules (rubric/extraction_rules.yaml)
```
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
```

# Project Structure
```
doc-refinery-agent/
doc-refinery-agent/
├── src/
│   ├── agents/
│   │   ├── triage.py              # Document classification
│   │   ├── domain_classifier.py   # Pluggable domain detection
│   │   └── query_agent.py         # Query with provenance
│   ├── strategies/
│   │   ├── base.py                # Base extractor class
│   │   ├── fast_text.py           # Strategy A
│   │   ├── layout_aware.py        # Strategy B (Docling)
│   │   ├── vision_ocr.py          # Strategy C (RapidOCR)
│   │   └── router.py              # Confidence-gated routing
│   ├── chunker/
│   │   ├── semantic_chunker.py    # 5 constitutional rules
│   │   └── page_index.py          # Hierarchical index
│   ├── vector_store/
│   │   └── vector_db.py           # LanceDB integration
│   └── models/
│       └── schemas.py             # Pydantic models
├── tests/
│   ├── test_triage.py             # Phase 1 tests (14)
│   └── test_phase2.py             # Phase 2 tests (12)
├── demo.py                         # Full pipeline demo
├── main.py                         # Entry point
└── .refinery/
    ├── extraction_ledger.jsonl    # Provenance tracking
    └── profiles/                   # Document profiles
---

### **Step 3: Commit README Update**

```powershell
# Add README
git add README.md

# Commit
git commit -m "docs: update README with full architecture documentation

- Added 6-step pipeline diagram
- Documented 5 constitutional rules
- Documented 3 extraction strategies
- Added project structure
- Added pipeline results (49 documents)
- Added testing instructions"

# Push
git push origin feature/advanced-extraction-chunking
```

### 6-Step Pipeline

| Step | Component | Description |
|------|-----------|-------------|
| **1** | Triage Agent | Document classification (origin, layout, domain) |
| **2** | Extraction Router | Confidence-gated strategy selection (A/B/C) |
| **3** | Multi-Strategy Extraction | Fast text, Layout-aware, VLM/OCR |
| **4** | Semantic Chunking | 5 constitutional rules for RAG quality |
| **5** | PageIndex Builder | Hierarchical document navigation |
| **6** | Query Agent | Questions with full provenance chain |

### 5 Constitutional Rules (Semantic Chunking)

1. ✅ Table cells never split from headers
2. ✅ Figure captions stored as metadata
3. ✅ Numbered lists kept as single LDU
4. ✅ Section headers as parent metadata
5. ✅ Cross-references resolved

### 3 Extraction Strategies

| Strategy | Best For | Confidence Threshold |
|----------|----------|---------------------|
| **A (Fast Text)** | Native digital, single column | 0.85 |
| **B (Layout-Aware)** | Table-heavy, multi-column | 0.75 |
| **C (VLM/OCR)** | Scanned, image-based | 0.70 |

## 🧪 Testing

```bash
# Phase 1 Tests (14 tests)
uv run pytest tests/test_triage.py -v

# Phase 2 Tests (12 tests)
uv run pytest tests/test_phase2.py -v

# Full Pipeline Demo
uv run python demo.py

# License
MIT License
Copyright (c) 2026 Document Intelligence Refinery Team
Contact
Repository: https://github.com/hydropython/doc-refinery-agent
Version: 1.0.0
Last Updated: 2026-03-03