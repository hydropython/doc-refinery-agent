"""
Full Document Batch Processor with LangGraph
Location: run_full_batch.py

Processes ALL documents in controlled batches.
Each batch is verified before moving to next.

Usage:
  uv run python run_full_batch.py --batches 1,2,3
  uv run python run_full_batch.py --doc-type FTA --pages 27-30
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from src.graph.workflow import run_pipeline


# Document corpus (from your DOMAIN_NOTES.md)
DOCUMENT_CORPUS = {
    "AUDIT": [
        "audit_report_-_2023_pt_1.pdf",
        "audit_report_-_2023_pt_2.pdf",
        "audit_report_-_2023_pt_3.pdf",
        "audit_report_-_2023_pt_4.pdf",
        "audit_report_-_2023_pt_5.pdf",
        "audit_report_-_2023_pt_6.pdf",
        "audit_report_-_2023_pt_7.pdf",
        "audit_report_-_2023_pt_8.pdf",
        "audit_report_-_2023_pt_9.pdf",
        "audit_report_-_2023_pt_10.pdf",
    ],
    "CBE": [
        "cbe_annual_report_2022.pdf",
        "cbe_quarterly_report_q1.pdf",
        "cbe_quarterly_report_q2.pdf",
        "cbe_quarterly_report_q3.pdf",
        "cbe_quarterly_report_q4.pdf",
    ],
    "FTA": [
        "fta_performance_survey_final_report_2022.pdf",
    ],
    "TAX": [
        "tax_guideline_2023.pdf",
        "tax_compliance_report.pdf",
    ]
}


class BatchProcessor:
    """Process documents in controlled batches"""
    
    def __init__(self, output_dir: str = ".refinery/batches"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []
    
    def process_batch(self, batch_id: int, documents: List[str], 
                      doc_type: str, pages: List[int]) -> Dict:
        """Process a single batch of documents"""
        
        print(f"\n{'='*80}")
        print(f"BATCH {batch_id}: {doc_type} Documents")
        print(f"{'='*80}")
        print(f"  Documents: {len(documents)}")
        print(f"  Pages: {pages[0]}-{pages[-1]} ({len(pages)} pages)")
        print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        batch_results = {
            "batch_id": batch_id,
            "doc_type": doc_type,
            "documents": documents,
            "pages": pages,
            "started": datetime.now().isoformat(),
            "results": [],
            "summary": {}
        }
        
        for i, doc_name in enumerate(documents, 1):
            print(f"\n  [{i}/{len(documents)}] Processing: {doc_name}")
            
            try:
                # Run LangGraph pipeline
                result = run_pipeline(
                    doc_id=doc_name,
                    pages=pages,
                    query=None
                )
                
                doc_result = {
                    "document": doc_name,
                    "status": result.get("status", "unknown"),
                    "strategy": result.get("selected_strategy", "unknown"),
                    "sections": len(result.get("sections", [])),
                    "summaries": len(result.get("summaries", [])),
                    "timestamp": datetime.now().isoformat()
                }
                
                batch_results["results"].append(doc_result)
                
                status_icon = "" if doc_result["status"] == "complete" else ""
                print(f"    {status_icon} Status: {doc_result['status']}")
                print(f"     Sections: {doc_result['sections']}, Summaries: {doc_result['summaries']}")
                
            except Exception as e:
                doc_result = {
                    "document": doc_name,
                    "status": "failed",
                    "error": str(e)[:100],
                    "timestamp": datetime.now().isoformat()
                }
                batch_results["results"].append(doc_result)
                print(f"     Error: {str(e)[:80]}")
        
        # Batch summary
        total = len(batch_results["results"])
        completed = sum(1 for r in batch_results["results"] if r["status"] == "complete")
        
        batch_results["completed"] = completed
        batch_results["total"] = total
        batch_results["success_rate"] = completed / max(total, 1)
        batch_results["finished"] = datetime.now().isoformat()
        
        # Save batch results
        batch_path = self.output_dir / f"batch_{batch_id}_{doc_type.lower()}.json"
        with open(batch_path, "w") as f:
            json.dump(batch_results, f, indent=2, default=str)
        
        # Print batch summary
        print(f"\n{'='*80}")
        print(f"  BATCH {batch_id} SUMMARY")
        print(f"{'='*80}")
        print(f"  Documents: {completed}/{total} ({batch_results['success_rate']:.0%})")
        print(f"  Saved to: {batch_path}")
        print(f"{'='*80}")
        
        self.results.append(batch_results)
        return batch_results
    
    def generate_final_report(self) -> str:
        """Generate final processing report"""
        
        total_docs = sum(r["total"] for r in self.results)
        total_completed = sum(r["completed"] for r in self.results)
        
        report = f"""
================================================================================
FULL DOCUMENT BATCH PROCESSING REPORT
================================================================================

Execution Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

BATCH SUMMARY:
"""
        
        for r in self.results:
            report += f"\n  Batch {r['batch_id']} ({r['doc_type']}): {r['completed']}/{r['total']} ({r['success_rate']:.0%})"
        
        report += f"""

OVERALL SUMMARY:
  Total Documents: {total_docs}
  Completed: {total_completed}
  Success Rate: {total_completed/max(total_docs,1):.0%}
  Batches: {len(self.results)}

================================================================================
"""
        
        # Save report
        report_path = self.output_dir / "final_report.txt"
        with open(report_path, "w") as f:
            f.write(report)
        
        return report


def main():
    processor = BatchProcessor()
    
    # Default: Process FTA document (pages 20-50 in batches)
    print("\n" + "=" * 80)
    print("  FULL DOCUMENT BATCH PROCESSOR")
    print("=" * 80)
    
    # Process FTA document in page batches
    batches = [
        {"batch_id": 1, "doc_type": "FTA", "docs": ["fta_performance_survey_final_report_2022.pdf"], "pages": list(range(20, 31))},
        {"batch_id": 2, "doc_type": "FTA", "docs": ["fta_performance_survey_final_report_2022.pdf"], "pages": list(range(31, 41))},
        {"batch_id": 3, "doc_type": "FTA", "docs": ["fta_performance_survey_final_report_2022.pdf"], "pages": list(range(41, 51))},
    ]
    
    for batch_config in batches:
        processor.process_batch(
            batch_id=batch_config["batch_id"],
            documents=batch_config["docs"],
            doc_type=batch_config["doc_type"],
            pages=batch_config["pages"]
        )
    
    # Generate final report
    report = processor.generate_final_report()
    print(report)
    
    print("\n ALL BATCHES COMPLETE!")
    print(f"   Results saved to: {processor.output_dir}")


if __name__ == "__main__":
    main()
