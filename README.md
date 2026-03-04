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
├── src/
│   ├── agents/
│   │   ├── triage.py
│   │   ├── chunker.py
│   │   └── query.py
│   ├── strategies/
│   │   ├── base.py
│   │   ├── fast_text.py
│   │   └── vision_ocr.py
│   ├── models/
│   │   └── schemas.py
│   └── indexer/
│       └── chroma_indexer.py
├── research/
│   ├── density_profiler.py
│   ├── quality_checker.py
│   └── benchmark_docling.py
├── rubric/
│   └── extraction_rules.yaml
├── data/
│   ├── chunk_audit/
│   ├── chunk_cbe/
│   ├── chunk_fta/
│   └── chunk_tax/
├── .refinery/
│   ├── extraction_ledger.jsonl
│   ├── profiles/
│   └── *.csv
├── main.py
├── pyproject.toml
├── DOMAIN_NOTES.md
└── README.md
```

# License
MIT License
Copyright (c) 2026 Document Intelligence Refinery Team
Contact
Repository: https://github.com/hydropython/doc-refinery-agent
Version: 1.0.0
Last Updated: 2026-03-03