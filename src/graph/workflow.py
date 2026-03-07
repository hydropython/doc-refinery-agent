"""
LangGraph Workflow Definition
Location: src/graph/workflow.py
"""

from langgraph.graph import StateGraph, END
from src.graph.state import DocumentState
from src.graph.nodes import PipelineNodes


def create_workflow() -> StateGraph:
    """Create the LangGraph workflow"""
    
    nodes = PipelineNodes()
    workflow = StateGraph(DocumentState)
    
    # Add nodes
    workflow.add_node("triage", nodes.triage_node)
    workflow.add_node("extract", nodes.extract_node)
    workflow.add_node("chunk", nodes.chunk_node)
    workflow.add_node("index", nodes.index_node)
    workflow.add_node("summarize", nodes.summarize_node)
    workflow.add_node("query", nodes.query_node)
    workflow.add_node("finalize", nodes.finalize_node)
    
    # Define edges
    workflow.set_entry_point("triage")
    workflow.add_edge("triage", "extract")
    workflow.add_edge("extract", "chunk")
    workflow.add_edge("chunk", "index")
    workflow.add_edge("index", "summarize")
    workflow.add_edge("summarize", "query")
    workflow.add_edge("query", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


def run_pipeline(doc_id: str = "1", pages: list = None, query: str = None) -> DocumentState:
    """Run the full LangGraph pipeline"""
    
    print("\n" + "=" * 70)
    print("  LANGGRAPH MULTI-AGENT PIPELINE")
    print("=" * 70)
    
    initial_state: DocumentState = {
        "doc_id": doc_id,
        "pdf_path": f"data/doc_{doc_id}.pdf",
        "pages": pages or [27, 28, 29],
        "query": query,
        "status": "pending",
        "errors": []
    }
    
    app = create_workflow()
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 70)
    print("  PIPELINE COMPLETE")
    print("=" * 70)
    
    return final_state
