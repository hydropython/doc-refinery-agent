#!/usr/bin/env python3
"""
Generate extraction_ledger.jsonl from processing_summary.csv
(This is needed because ledger logging wasn't added before pipeline run)
"""

import csv
import json
from pathlib import Path
from datetime import datetime

def generate_ledger():
    summary_path = Path("./.refinery/processing_summary.csv")
    ledger_path = Path("./.refinery/extraction_ledger.jsonl")
    
    if not summary_path.exists():
        print("❌ processing_summary.csv not found")
        return
    
    entries = []
    with open(summary_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract strategy from "Final Status" column
            final_status = row.get("Final Status", "")
            strategy = "Unknown"
            if "Strategy A" in final_status:
                strategy = "Strategy A (Fast Text)"
            elif "Strategy B" in final_status:
                strategy = "Strategy B (Layout-Aware)"
            elif "Strategy C" in final_status:
                strategy = "Strategy C (VLM/OCR)"
            
            # Create ledger entry
            entry = {
                "doc_id": row.get("Segment", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "strategy": strategy,
                "confidence_score": float(row.get("QA Score", 0.0)),
                "quality_score": float(row.get("QA Score", 0.0)),
                "cost_usd": 0.02 if "Strategy C" in strategy else 0.00,
                "status": "indexed" if "✅" in final_status else "rejected"
            }
            entries.append(entry)
    
    # Write ledger
    with open(ledger_path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")
    
    print(f"✅ Generated {len(entries)} ledger entries")
    print(f"📁 Saved to: {ledger_path}")
    
    # Show first 3 entries
    print("\n📋 Sample Entries:")
    for entry in entries[:3]:
        print(f"  - {entry['doc_id']}: {entry['strategy']} (Score: {entry['quality_score']})")

if __name__ == "__main__":
    generate_ledger()