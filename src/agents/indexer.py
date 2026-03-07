"""
Indexer Agent with PageIndex Support
Location: src/agents/indexer.py
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from loguru import logger

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class SectionNode:
    """Section in PageIndex"""
    
    def __init__(self, title: str):
        self.title = title
        self.pages: List[int] = []
        self.ldus: List[Any] = []
        self.summary: str = ""
        self.tables: List[Dict] = []
    
    def add_table(self, table_data: Dict):
        """Add table with row/column structure"""
        self.tables.append({
            "table_id": f"Table_{len(self.tables) + 1}",
            "rows": table_data.get("rows", 0),
            "columns": table_data.get("columns", 0),
            "headers": table_data.get("headers", []),
            "cells": table_data.get("cells", []),
            "bbox": table_data.get("bbox", []),
            "page": table_data.get("page", 0)
        })
    
    def dict(self) -> Dict:
        return {
            "title": self.title,
            "pages": self.pages,
            "ldus": [ldu.__dict__ if hasattr(ldu, '__dict__') else ldu for ldu in self.ldus],
            "summary": self.summary,
            "tables": self.tables
        }


class PageIndex:
    """PageIndex with table structure support"""
    
    def __init__(self):
        self.sections: Dict[str, SectionNode] = {}
        self.doc_id: str = ""
        self.source_path: str = ""
    
    def build_index(self, ldus: List[Any]) -> None:
        """Build PageIndex from LDUs (handles both dict and LDU objects)"""
        logger.info(f"Building PageIndex from {len(ldus)} LDUs...")
        
        section_map: Dict[str, List[Any]] = {}
        for ldu in ldus:
            # Handle LDU object (pydantic) vs dict
            if hasattr(ldu, 'section'):
                section = ldu.section
            elif isinstance(ldu, dict):
                section = ldu.get("section", "General")
            else:
                section = "General"
            
            if section not in section_map:
                section_map[section] = []
            section_map[section].append(ldu)
        
        for title, section_ldus in section_map.items():
            node = SectionNode(title)
            for ldu in section_ldus:
                # Handle LDU object vs dict
                if hasattr(ldu, 'page'):
                    node.pages.append(ldu.page)
                elif isinstance(ldu, dict):
                    node.pages.append(ldu.get("page", 0))
                else:
                    node.pages.append(0)
                node.ldus.append(ldu)
            self.sections[title] = node
        
        logger.info(f"Created {len(self.sections)} sections")
    
    def add_tables(self, tables: List[Dict]) -> None:
        """Add table structure to PageIndex"""
        logger.info(f"Adding {len(tables)} tables to PageIndex...")
        
        for table in tables:
            page = table.get("page", 0)
            section = table.get("section", "Tables & Figures")
            
            if section in self.sections:
                self.sections[section].add_table(table)
            else:
                node = SectionNode(section)
                node.pages = [page]
                node.add_table(table)
                self.sections[section] = node
        
        logger.info(f"Added {len(tables)} tables")
    
    def add_summaries(self, use_llm: bool = True) -> None:
        """Generate summaries for sections"""
        logger.info("Generating LLM summaries for sections...")
        
        if not use_llm or not OPENAI_AVAILABLE:
            for section in self.sections.values():
                section.summary = "[Summary disabled - offline mode]"
            return
        
        client = OpenAI()
        
        for i, (title, node) in enumerate(self.sections.items(), 1):
            print(f"    [{i}/{len(self.sections)}] {title}...", end=" ")
            
            # Get content from LDUs
            content_parts = []
            for ldu in node.ldus:
                if hasattr(ldu, 'content'):
                    content_parts.append(ldu.content[:500])
                elif isinstance(ldu, dict):
                    content_parts.append(ldu.get("content", "")[:500])
            
            content = "\n".join(content_parts)[:1000]
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Summarize in 1 sentence."},
                        {"role": "user", "content": content}
                    ],
                    max_tokens=50
                )
                node.summary = response.choices[0].message.content
            except Exception as e:
                node.summary = f"[Summary unavailable: {str(e)[:50]}]"
            
            print("Done")
        
        logger.info(f"Generated {len(self.sections)} summaries")
    
    def print_tree(self) -> None:
        """Print PageIndex tree"""
        print("\n" + "="*70)
        print("  PAGEINDEX TREE")
        print("="*70)
        print("  Document/")
        
        for title, node in self.sections.items():
            print(f"     {title}/")
            summary_preview = node.summary[:60] + "..." if len(node.summary) > 60 else node.summary
            print(f"        Summary: {summary_preview}")
            print(f"        Pages: {node.pages}")
            print(f"        LDUs: {len(node.ldus)}")
        
        print("="*70)
    
    def save(self, output_path: str) -> str:
        """Save PageIndex to JSON"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "doc_id": self.doc_id,
            "source_path": self.source_path,
            "sections": {title: node.dict() for title, node in self.sections.items()}
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Saved PageIndex to {output_path}")
        return output_path


class IndexerAgent:
    """Indexer Agent wrapper - uses PageIndex internally"""
    
    def __init__(self):
        self.page_index = PageIndex()
        logger.info("IndexerAgent initialized (openai for summaries)")
    
    def build_index(self, ldus: List[Any]) -> None:
        """Build PageIndex from LDUs"""
        self.page_index.build_index(ldus)
    
    def add_summaries(self, use_llm: bool = True) -> None:
        """Generate summaries"""
        self.page_index.add_summaries(use_llm)
    
    def print_tree(self) -> None:
        """Print PageIndex tree"""
        self.page_index.print_tree()
    
    def save(self, output_path: str) -> str:
        """Save PageIndex"""
        return self.page_index.save(output_path)
    
    @property
    def sections(self) -> Dict[str, SectionNode]:
        """Access sections"""
        return self.page_index.sections
