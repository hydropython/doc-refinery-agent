"""
Integrated Precision/Recall Evaluation Module
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class EvaluationResult:
    page: int
    content_type: str
    expected: int
    extracted: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1_score: float


class PipelineEvaluator:
    """Integrated evaluation for document refinement pipeline"""
    
    def __init__(self):
        self.ground_truth = {}
        self.extractions = {}
    
    def add_ground_truth(self, page: int, content_type: str, 
                         expected_count: int):
        """Add ground truth annotation for a page"""
        self.ground_truth[page] = {
            "content_type": content_type,
            "expected": expected_count
        }
    
    def add_extraction_result(self, page: int, extracted_count: int):
        """Add system extraction result for a page"""
        self.extractions[page] = {
            "extracted": extracted_count
        }
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate precision/recall for each content type"""
        results = {
            "overall": {"tp": 0, "fp": 0, "fn": 0, "precision": 0, "recall": 0, "f1": 0},
            "by_type": {},
            "by_page": []
        }
        
        by_type = {}
        
        for page, gt in self.ground_truth.items():
            content_type = gt["content_type"]
            expected = gt["expected"]
            ext = self.extractions.get(page, {"extracted": 0})
            extracted = ext["extracted"]
            
            tp = min(expected, extracted)
            fp = max(0, extracted - expected)
            fn = max(0, expected - extracted)
            
            results["overall"]["tp"] += tp
            results["overall"]["fp"] += fp
            results["overall"]["fn"] += fn
            
            if content_type not in by_type:
                by_type[content_type] = {"tp": 0, "fp": 0, "fn": 0}
            by_type[content_type]["tp"] += tp
            by_type[content_type]["fp"] += fp
            by_type[content_type]["fn"] += fn
            
            precision = tp / max(tp + fp, 1)
            recall = tp / max(tp + fn, 1)
            f1 = 2 * precision * recall / max(precision + recall, 0.001)
            
            results["by_page"].append({
                "page": page,
                "content_type": content_type,
                "expected": expected,
                "extracted": extracted,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3)
            })
        
        total = results["overall"]
        total["precision"] = round(total["tp"] / max(total["tp"] + total["fp"], 1), 3)
        total["recall"] = round(total["tp"] / max(total["tp"] + total["fn"], 1), 3)
        total["f1"] = round(2 * total["precision"] * total["recall"] / max(total["precision"] + total["recall"], 0.001), 3)
        
        for content_type, metrics in by_type.items():
            precision = metrics["tp"] / max(metrics["tp"] + metrics["fp"], 1)
            recall = metrics["tp"] / max(metrics["tp"] + metrics["fn"], 1)
            f1 = 2 * precision * recall / max(precision + recall, 0.001)
            
            results["by_type"][content_type] = {
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "fn": metrics["fn"],
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3)
            }
        
        return results
    
    def save_results(self, output_path: str):
        """Save evaluation results to JSON"""
        results = self.calculate_metrics()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        return output_path
    
    def print_report(self):
        """Print human-readable evaluation report"""
        results = self.calculate_metrics()
        
        print("=" * 80)
        print("PIPELINE EVALUATION REPORT")
        print("=" * 80)
        
        print("\n OVERALL METRICS")
        print("-" * 40)
        o = results["overall"]
        print(f"  True Positives:  {o['tp']}")
        print(f"  False Positives: {o['fp']}")
        print(f"  False Negatives: {o['fn']}")
        print(f"  Precision:       {o['precision']:.1%}")
        print(f"  Recall:          {o['recall']:.1%}")
        print(f"  F1 Score:        {o['f1']:.1%}")
        
        print("\n BY CONTENT TYPE")
        print("-" * 40)
        for ctype, metrics in results["by_type"].items():
            print(f"\n  {ctype.upper()}:")
            print(f"    Precision: {metrics['precision']:.1%}")
            print(f"    Recall:    {metrics['recall']:.1%}")
            print(f"    F1 Score:  {metrics['f1']:.1%}")
        
        print("\n BY PAGE")
        print("-" * 40)
        for page_result in results["by_page"]:
            print(f"  Page {page_result['page']} ({page_result['content_type']}): "
                  f"P={page_result['precision']:.0%}, R={page_result['recall']:.0%}, F1={page_result['f1']:.0%}")
        
        print("\n" + "=" * 80)
        
        return results
