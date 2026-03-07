"""
4-Stage Demo - Uses REAL LangGraph Workflow
Location: run_4stage_demo.py

This script ONLY calls workflow.invoke()
All work is done by LangGraph nodes  agents
"""

import json
from pathlib import Path
from datetime import datetime
from src.graph.workflow import run_pipeline


def main():
    pdf_path = "data/fta_performance_survey_final_report_2022.pdf"
    pages = [34]
    
    print("\n" + "=" * 80)
    print("  DOCUMENT INTELLIGENCE REFINERY  |  v1.0")
    print("  REAL LangGraph Multi-Agent Pipeline")
    print("=" * 80)
    print(f"  Document: {pdf_path}")
    print(f"  Pages: {pages[0]}-{pages[-1]}")
    print("=" * 80 + "\n")
    
    # ONLY call the LangGraph workflow
    # All work is done by nodes  agents
    result = run_pipeline(
        doc_id="fta_test",
        pages=pages,
        query="What content is on these pages?"
    )
    
    # Display results
    print("\n" + "=" * 80)
    print("  PIPELINE RESULTS")
    print("=" * 80)
    
    print(f"\n   Strategy: {result.get('selected_strategy', 'N/A')}")
    print(f"   Chars Extracted: {result.get('char_count', 0):,}")
    print(f"   Quality: {result.get('extraction_quality', 0):.2f}")
    print(f"   Confidence: {result.get('extraction_confidence', 0):.2f}")
    print(f"   Sections: {len(result.get('sections', []))}")
    print(f"   Summaries: {len(result.get('summaries', []))}")
    print(f"   Status: {result.get('status', 'unknown')}")
    
    # Save results
    output_path = Path(".refinery/langgraph_results.json")
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n  Results saved to: {output_path}")
    print("\n" + "=" * 80)
    print("  PIPELINE COMPLETE!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
