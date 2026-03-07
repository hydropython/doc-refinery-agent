"""
PageIndex Indexer Agent
Location: src/agents/indexer.py

Builds PageIndex tree with LLM-generated section summaries.
Supports navigation without vector search.
"""

import json
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from loguru import logger
from src.agents.summary_generator import SummaryGenerator


class PageIndexNode:
    """Node in PageIndex tree"""
    
    def __init__(self, title: str, pages: List[int] = None, ldus: List[str] = None):
        self.title = title
        self.summary: str = None
        self.pages = pages or []
        self.ldus = ldus or []
        self.children: List["PageIndexNode"] = []
        self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "pages": sorted(list(set(self.pages))),
            "ldus": self.ldus,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children]
        }


class IndexerAgent:
    """
    PageIndex Indexer Agent
    
    Usage:
        agent = IndexerAgent()
        page_index = agent.build_index(ldus)
    """
    
    def __init__(self, summary_provider: str = "openai"):
        self.summary_generator = SummaryGenerator()
        self.root = PageIndexNode(title="Document")
        self.sections: Dict[str, PageIndexNode] = {}
        logger.info(f"IndexerAgent initialized ({summary_provider} for summaries)")
    
    def build_index(self, ldus: List[Dict]) -> Dict:
        """
        Build PageIndex tree from LDUs
        
        Args:
            ldus: List of LDU dicts
        
        Returns:
            PageIndex tree dict
        """
        logger.info(f"Building PageIndex from {len(ldus)} LDUs...")
        
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
            node.metadata["content_preview"] = ldu.get("content", "")[:800]
        
        logger.info(f"Created {len(self.sections)} sections")
        return self.to_dict()
    
    def add_summaries(self) -> None:
        """Generate LLM summaries for all sections"""
        logger.info("Generating LLM summaries for sections...")
        
        sections_for_summary = []
        for title, node in self.sections.items():
            if not node.summary:
                content = node.metadata.get("content_preview", f"Section: {title}")
                sections_for_summary.append({
                    "title": title,
                    "content": content
                })
        
        if sections_for_summary:
            results = self.summary_generator.generate_batch(sections_for_summary)
            for result in results:
                self.sections[result["title"]].summary = result["summary"]
        
        logger.info(f"Generated {len(sections_for_summary)} summaries")
    
    def to_dict(self) -> Dict:
        """Convert tree to dictionary"""
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
        logger.info(f"Saved PageIndex to {output_path}")
        return output_path
    
    def navigate(self, section_title: str) -> Dict:
        """Navigate to specific section"""
        if section_title in self.sections:
            node = self.sections[section_title]
            return {
                "title": node.title,
                "summary": node.summary,
                "pages": node.pages,
                "ldus": node.ldus
            }
        return None
    
    def print_tree(self) -> None:
        """Print tree visualization"""
        print("\n" + "=" * 70)
        print("  PAGEINDEX TREE")
        print("=" * 70)
        print("  Document/")
        for node in self.root.children:
            summary_preview = (node.summary[:50] + "...") if node.summary else "[No summary]"
            print(f"     {node.title}/")
            print(f"        Summary: {summary_preview}")
            print(f"        Pages: {sorted(list(set(node.pages)))}")
            print(f"        LDUs: {len(node.ldus)}")
        print("=" * 70)
