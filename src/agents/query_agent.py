"""
Query Agent with 3 Tools
Location: src/agents/query_agent.py

Tools:
1. pageindex_navigate - Navigate PageIndex tree
2. semantic_search - Search vector store
3. structured_query - Query structured data
"""

from typing import Dict, List, Optional
from loguru import logger
import json


class QueryAgent:
    """
    Query Agent with 3 Tools
    
    Usage:
        agent = QueryAgent(page_index, vector_store)
        result = agent.query("What content is on page 27?")
    """
    
    def __init__(self, page_index: Dict = None, vector_store = None):
        self.page_index = page_index
        self.vector_store = vector_store
        self.tools = {
            "pageindex_navigate": self.pageindex_navigate,
            "semantic_search": self.semantic_search,
            "structured_query": self.structured_query
        }
        logger.info("QueryAgent initialized with 3 tools")
    
    def query(self, question: str) -> Dict:
        """
        Answer question using appropriate tool
        
        Args:
            question: Natural language question
        
        Returns:
            Dict with answer and provenance
        """
        logger.info(f"Processing query: {question}")
        
        # Simple routing based on question type
        if "page" in question.lower() or "section" in question.lower():
            tool_result = self.pageindex_navigate(question)
            tool_used = "pageindex_navigate"
        elif "search" in question.lower() or "find" in question.lower():
            tool_result = self.semantic_search(question)
            tool_used = "semantic_search"
        else:
            tool_result = self.structured_query(question)
            tool_used = "structured_query"
        
        return {
            "question": question,
            "answer": tool_result.get("answer", "No answer found"),
            "tool_used": tool_used,
            "provenance": tool_result.get("provenance", {}),
            "confidence": tool_result.get("confidence", 0.0)
        }
    
    def pageindex_navigate(self, query: str) -> Dict:
        """Tool 1: Navigate PageIndex tree (NO vector search)"""
        logger.info("Using tool: pageindex_navigate")
        
        # Extract page/section from query
        import re
        page_match = re.search(r'page\s*(\d+)', query.lower())
        
        if page_match and self.page_index:
            page_num = int(page_match.group(1))
            
            # Find section containing this page
            for section_name, section_data in self.page_index.get("sections", {}).items():
                if page_num in section_data.get("pages", []):
                    return {
                        "answer": f"Page {page_num} is in section '{section_name}'. {section_data.get('summary', '')}",
                        "provenance": {
                            "page": page_num,
                            "section": section_name,
                            "pages": section_data.get("pages", []),
                            "ldus": section_data.get("ldus", [])
                        },
                        "confidence": 0.95
                    }
        
        return {
            "answer": "Page not found in index",
            "provenance": {},
            "confidence": 0.0
        }
    
    def semantic_search(self, query: str) -> Dict:
        """Tool 2: Search vector store"""
        logger.info("Using tool: semantic_search")
        
        # Placeholder - integrate with LanceDB/ChromaDB
        return {
            "answer": "Semantic search results would appear here",
            "provenance": {"tool": "semantic_search"},
            "confidence": 0.80
        }
    
    def structured_query(self, query: str) -> Dict:
        """Tool 3: Query structured data (tables)"""
        logger.info("Using tool: structured_query")
        
        # Placeholder - integrate with table data
        return {
            "answer": "Structured query results would appear here",
            "provenance": {"tool": "structured_query"},
            "confidence": 0.85
        }
    
    def list_tools(self) -> List[str]:
        """List available tools"""
        return list(self.tools.keys())
