"""
Document Intelligence Refinery - LangGraph Version
Run: uv run python run_refinery.py --doc 1 --pages 27-29
"""

import sys
import argparse
from src.graph.workflow import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Document Intelligence Refinery")
    parser.add_argument("--doc", type=str, default="1", help="Document ID")
    parser.add_argument("--pages", type=str, default="27,28,29", help="Pages to process")
    parser.add_argument("--query", type=str, default=None, help="Natural language query")
    
    args = parser.parse_args()
    
    # Parse pages
    if "-" in args.pages:
        start, end = args.pages.split("-")
        pages = list(range(int(start), int(end) + 1))
    else:
        pages = [int(p.strip()) for p in args.pages.split(",")]
    
    # Run LangGraph pipeline
    result = run_pipeline(
        doc_id=args.doc,
        pages=pages,
        query=args.query
    )
    
    # Print results
    print("\n" + "=" * 70)
    print("  FINAL RESULTS")
    print("=" * 70)
    print(f"  Status: {result.get('status', 'unknown')}")
    print(f"  Pages: {result.get('pages', [])}")
    print(f"  Strategy: {result.get('selected_strategy', 'unknown')}")
    print(f"  Sections: {len(result.get('sections', []))}")
    print(f"  Summaries: {len(result.get('summaries', []))}")
    
    if result.get("answer"):
        print(f"\n  Query Answer: {result['answer']}")
        print(f"  Provenance: Page {result.get('provenance', {}).get('page', 'N/A')}")
    
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
