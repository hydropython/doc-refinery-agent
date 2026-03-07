# Document Intelligence Refinery

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-Green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Phase_0_Complete-Blue?style=for-the-badge)](https://github.com/hydropython/doc-refinery-agent)
[![Pipeline](https://img.shields.io/badge/Pipeline-49/49_Success-BrightGreen?style=for-the-badge)](https://github.com/hydropython/doc-refinery-agent)

---
## Overview

The Document Intelligence Refinery is an enterprise-grade document extraction and RAG pipeline designed to process heterogeneous financial documents with multi-strategy extraction, confidence-gated routing, and full provenance tracking.

## 📌 Overview

A production-ready document intelligence pipeline that extracts text, tables, and chart data from PDFs (both digital and scanned), creates searchable knowledge units with provenance tracking, and answers natural language queries - **100% locally** with **zero cloud dependencies**.





---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔒 **100% Local** | No API calls, no cloud dependencies, no data leaves your machine |
| 💰 **$0.00 Cost** | Free and open source - no per-page charges |
| 📊 **Chart Extraction** | OCR captures percentages, labels, and values from charts/graphs |
| 📍 **Provenance Tracking** | Every answer includes page number + bounding box location |
| 💬 **Natural Language Query** | Ask questions in plain English, get answers with sources |
| 📈 **Precision/Recall Metrics** | Built-in evaluation module for quality assessment |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

```bash
# Clone repository
git clone https://github.com/hydropython/doc-refinery-agent.git
cd doc-refinery-agent

# Checkout feature branch
git checkout feature/advanced-extraction-chunking

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e .
### Multi-Strategy Extraction
```

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

---


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
## process for specfic page 
uv run python run_refinery.py --doc <doc_id> --page <page_number>

# Example: Process chart page (Figure 3)
uv run python run_refinery.py --doc 3 --page 34

# Example: Process table page
uv run python run_refinery.py --doc 3 --page 27
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
│   │   ├── query_agent.py      # Natural language query
│   │   ├── triage.py           # Document classification
│   │   └── fact_table.py       # Structured data handling
│   ├── chunker/
│   │   ├── semantic_chunker.py # LDU creation with BBox
│   │   └── page_index.py       # Section indexing
│   ├── strategies/
│   │   ├── router.py           # Strategy selection
│   │   ├── layout_aware.py     # OCR extraction
│   │   └── vision_ocr.py       # Advanced OCR
│   ├── models/
│   │   └── schemas.py          # Data models
│   ├── vector_store/
│   │   └── vector_db.py        # LanceDB integration
│   └── evaluation/
│       └── metrics.py          # Precision/Recall
├── run_refinery.py             # Main entry point
├── demo.py                     # Demo script
├── pyproject.toml              # Dependencies
├── uv.lock                     # Locked versions
├── README.md                   # This file
└── .gitignore                  # Git ignore rules                 ✅ 49 document profiles
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
```
┌─────────────────────────────────────────────────────────────────────────┐
│ DOC REFINERY AGENT │
├─────────────────────────────────────────────────────────────────────────┤
│ 📥 Input → 🔍 Triage → 🎯 Router → 📥 Extract → ✂️ Chunk → 📑 Index │
│ ↓ │
│ ❓ Query ← 🗄️ Vector ← 🔗 Provenance ← 🤖 Query Agent │
└─────────────────────────────────────────────────────────────────────────┘


# License
MIT License
Copyright (c) 2026 Document Intelligence Refinery Team
Contact
Repository: https://github.com/hydropython/doc-refinery-agent
Version: 1.0.0
Last Updated: 2026-03-03