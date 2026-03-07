"""
LangGraph Pipeline Nodes - Uses YOUR Agents
Location: src/graph/nodes.py
"""

from datetime import datetime
from src.graph.state import DocumentState
from src.agents.triage import TriageAgent
from src.agents.extractor import ExtractionAgent
from src.agents.chunker import ChunkerAgent
from src.agents.indexer import IndexerAgent
from src.agents.query_agent import QueryAgent


class PipelineNodes:
    """All LangGraph nodes - Uses YOUR agents"""
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.extraction_agent = ExtractionAgent()
        self.chunker_agent = ChunkerAgent()
        self.indexer_agent = IndexerAgent()
        self.query_agent = None
        self.pdf_path = "data/fta_performance_survey_final_report_2022.pdf"
    
    def triage_node(self, state: DocumentState) -> DocumentState:
        """Node 1: Triage - Uses YOUR TriageAgent"""
        print("\n  [Node 1: Triage] Using TriageAgent...")
        
        try:
            # Call YOUR triage agent - returns COMPLETE DocumentProfile
            profile = self.triage_agent.analyze(self.pdf_path)
            
            state["document_profile"] = profile
            state["page_type"] = profile.origin_type.value if hasattr(profile.origin_type, 'value') else str(profile.origin_type)
            state["triage_confidence"] = profile.confidence_score
            state["selected_strategy"] = profile.recommended_strategy
            
            print(f"     Origin: {profile.origin_type}")
            print(f"     Layout: {profile.layout_complexity}")
            print(f"     Strategy: {profile.recommended_strategy}")
            print(f"     Confidence: {profile.confidence_score:.2f}")
            print(f"     Cost Tier: {profile.estimated_cost_tier}")
            
        except Exception as e:
            print(f"      Error: {str(e)[:80]}")
        
        state["timestamp"] = datetime.now().isoformat()
        return state
    
    def extract_node(self, state: DocumentState) -> DocumentState:
        """Node 2: Extract - Uses YOUR ExtractionAgent"""
        print("\n  [Node 2: Extract] Using ExtractionAgent...")
        
        try:
            profile = state.get("document_profile")
            
            if profile is None:
                print("      No profile from triage, running triage first")
                profile = self.triage_agent.analyze(self.pdf_path)
                state["document_profile"] = profile
            
            # Call YOUR extraction agent
            result, strategy = self.extraction_agent.extract(self.pdf_path, profile, state.get("pages", None))
            
            # Create LDUs
            all_ldus = []
            pages = state.get("pages", [1])
            for page_num in pages:
                content_lower = result.content[:800].lower() if result and result.content else ""
                
                if "executive" in content_lower or "summary" in content_lower:
                    section = "Executive Summary"
                elif "financial" in content_lower or "revenue" in content_lower:
                    section = "Financial Data"
                elif "table" in content_lower or "figure" in content_lower:
                    section = "Tables & Figures"
                else:
                    section = "General"
                
                all_ldus.append({
                    "id": f"LDU_{page_num}",
                    "page": page_num,
                    "section": section,
                    "content": result.content[:800] if result and result.content else "",
                    "char_count": len(result.content) // len(pages) if result and result.content else 0,
                    "bbox": [0, 0, 595, 842]
                })
            
            state["extracted_text"] = result.content if result else ""
            state["char_count"] = len(result.content) if result and result.content else 0
            state["extraction_quality"] = result.quality_score if result else 0.0
            state["extraction_confidence"] = result.quality_score if result else 0.0
            state["selected_strategy"] = strategy
            state["ldus"] = all_ldus
            
            print(f"     Strategy: {strategy}")
            print(f"     Chars: {state['char_count']:,}")
            print(f"     Quality: {state['extraction_quality']:.2f}")
            
        except Exception as e:
            print(f"      Error: {str(e)[:80]}")
            state["selected_strategy"] = "strategy_b"
            state["ldus"] = []
        
        return state
    
    def chunk_node(self, state: DocumentState) -> DocumentState:
        """Node 3: Chunk - Uses ChunkerAgent (5 rules)"""
        print("\n  [Node 3: Chunk] Using ChunkerAgent (5 rules)...")
        
        try:
            ldus = self.chunker_agent.chunk(
                state.get("extracted_text", ""),
                state.get("pages", []),
                sections=None
            )
            state["ldus"] = self.chunker_agent.to_dict(ldus)
            print(f"     LDUs: {len(ldus)} (5 rules validated)")
            
        except Exception as e:
            print(f"      Error: {str(e)[:80]}")
            state["ldus"] = []
        
        return state
    
    def index_node(self, state: DocumentState) -> DocumentState:
        """Node 4: Index - Uses IndexerAgent + GPT-4 summaries"""
        print("\n  [Node 4: Index] Using IndexerAgent...")
        
        try:
            self.indexer_agent.build_index(state.get("ldus", []))
            self.indexer_agent.add_summaries()
            self.indexer_agent.print_tree()
            
            output_path = self.indexer_agent.save(".refinery/page_index.json")
            
            state["sections"] = [
                {"title": title, "pages": node.pages, "ldus": node.ldus, "summary": node.summary}
                for title, node in self.indexer_agent.sections.items()
            ]
            
            self.query_agent = QueryAgent(page_index={"sections": state["sections"]})
            
            print(f"     Sections: {len(state['sections'])}, Saved: {output_path}")
            
        except Exception as e:
            print(f"      Error: {str(e)[:80]}")
        
        return state
    
    def summarize_node(self, state: DocumentState) -> DocumentState:
        """Node 5: Summaries (already in PageIndex)"""
        print("\n  [Node 5: Summaries] Generated in Indexer...")
        state["summaries"] = state.get("sections", [])
        return state
    
    def query_node(self, state: DocumentState) -> DocumentState:
        """Node 6: Query - Uses QueryAgent (3 tools)"""
        print("\n  [Node 6: Query] Using QueryAgent...")
        
        if self.query_agent and state.get("query"):
            result = self.query_agent.query(state["query"])
            state["answer"] = result["answer"]
            state["provenance"] = result["provenance"]
            print(f"     Tool: {result['tool_used']}, Confidence: {result['confidence']:.2f}")
        else:
            state["answer"] = "No query provided"
            state["provenance"] = {}
        
        return state
    
    def finalize_node(self, state: DocumentState) -> DocumentState:
        """Node 7: Finalize"""
        print("\n  [Node 7: Finalize] Completing...")
        state["status"] = "complete"
        return state
