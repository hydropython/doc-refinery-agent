"""
PageIndex Builder with Tree Visualization
Location: src/chunker/page_index.py

Builds hierarchical section tree from LDUs.
Each section gets a GPT-4 Mini summary.
"""

import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime


class PageIndexNode:
    """A node in the PageIndex tree"""
    
    def __init__(self, title: str, pages: List[int] = None, ldus: List[str] = None):
        self.title = title
        self.summary: Optional[str] = None
        self.pages = pages or []
        self.ldus = ldus or []
        self.children: List["PageIndexNode"] = []
        self.metadata = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "summary": self.summary,
            "pages": sorted(list(set(self.pages))),
            "ldus": self.ldus,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children]
        }
    
    def print_tree(self, indent: int = 0) -> str:
        """Print tree visualization"""
        prefix = "  " * indent
        summary_preview = (self.summary[:50] + "...") if self.summary else "[No summary]"
        
        lines = []
        lines.append(f"{prefix} {self.title}")
        lines.append(f"{prefix}   Summary: {summary_preview}")
        lines.append(f"{prefix}   Pages: {sorted(list(set(self.pages)))}")
        lines.append(f"{prefix}   LDUs: {len(self.ldus)}")
        
        for child in self.children:
            lines.extend(child.print_tree(indent + 1).split("\n"))
        
        return "\n".join(lines)


class PageIndexBuilder:
    """Build PageIndex tree from LDUs"""
    
    def __init__(self):
        self.root = PageIndexNode(title="Document")
        self.sections: Dict[str, PageIndexNode] = {}
    
    def build(self, ldus: List[Dict]) -> PageIndexNode:
        """
        Build PageIndex tree from LDUs
        
        Args:
            ldus: List of LDU dicts with page, section, content, id
        
        Returns:
            Root PageIndexNode
        """
        print("\n  [PageIndex] Building section tree...")
        
        # Group LDUs by section
        for ldu in ldus:
            section_title = ldu.get("section", "Unclassified")
            
            if section_title not in self.sections:
                node = PageIndexNode(title=section_title)
                self.sections[section_title] = node
                self.root.children.append(node)
            
            node = self.sections[section_title]
            node.pages.append(ldu.get("page", 0))
            node.ldus.append(ldu.get("id", ""))
            
            # Store content preview for summary
            if "content_preview" not in node.metadata:
                node.metadata["content_preview"] = ldu.get("content", "")[:800]
        
        print(f"     Sections created: {len(self.sections)}")
        
        return self.root
    
    def add_summaries(self, summary_generator) -> None:
        """Add GPT-4 Mini summaries to all sections"""
        print("\n  [PageIndex] Generating section summaries...")
        
        sections_for_summary = []
        for title, node in self.sections.items():
            if not node.summary:
                content = node.metadata.get("content_preview", f"Section: {title}")
                sections_for_summary.append({
                    "title": title,
                    "content": content
                })
        
        if sections_for_summary:
            results = summary_generator.generate_batch(sections_for_summary)
            for result in results:
                self.sections[result["title"]].summary = result["summary"]
        
        print(f"     Summaries generated: {len(sections_for_summary)}")
    
    def to_dict(self) -> Dict:
        """Convert entire tree to dictionary"""
        return {
            "document": "fta_performance_survey_final_report_2022.pdf",
            "timestamp": datetime.now().isoformat(),
            "total_sections": len(self.sections),
            "tree": self.root.to_dict()
        }
    
    def save(self, output_path: str) -> str:
        """Save PageIndex to JSON"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        return output_path
    
    def print_tree(self) -> None:
        """Print full tree visualization"""
        print("\n" + "=" * 70)
        print("  PAGEINDEX TREE")
        print("=" * 70)
        print(self.root.print_tree())
        print("=" * 70)
