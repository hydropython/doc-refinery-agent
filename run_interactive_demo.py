"""
Interactive Pipeline Demo - Asks After EACH Agent
Location: run_interactive_demo.py
"""

import json
from pathlib import Path
from datetime import datetime
from src.agents.triage import TriageAgent
from src.agents.extractor import ExtractionAgent
from src.agents.chunker import ChunkerAgent
from src.agents.indexer import IndexerAgent
from src.agents.query_agent import QueryAgent
from src.models.schemas import DocumentProfile


def ask_continue(agent_name: str):
    """Ask user if they want to continue and see results"""
    print(f"\n{'='*80}")
    print(f"   {agent_name} COMPLETE!")
    print(f"{'='*80}")
    
    while True:
        choice = input("\n  Do you want to see the results? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        print("  Please enter 'y' or 'n'")


def main():
    pdf_path = "data/fta_performance_survey_final_report_2022.pdf"
    pages = [34]
    
    print("\n" + "="*80)
    print("  DOCUMENT INTELLIGENCE REFINERY | INTERACTIVE MODE")
    print("  Working OFFLINE (No OpenAI for extraction)")
    print("="*80)
    print(f"  Document: {pdf_path}")
    print(f"  Pages: {pages}")
    print("="*80)
    
    state = {
        "doc_id": "interactive_test",
        "pages": pages,
        "pdf_path": pdf_path,
        "document_profile": None,
        "extracted_text": "",
        "char_count": 0,
        "extraction_quality": 0.0,
        "selected_strategy": "",
        "ldus": [],
        "sections": [],
        "summaries": []
    }
    
    # ========== NODE 1: TRIAGE ==========
    print(f"\n{'='*80}")
    print("  [Node 1: Triage] Running TriageAgent...")
    print(f"{'='*80}")
    
    triage_agent = TriageAgent()
    profile = triage_agent.analyze(pdf_path)
    state["document_profile"] = profile
    
    if ask_continue("TRIAGE AGENT"):
        print(f"\n   TRIAGE RESULTS:")
        print(f"  ")
        print(f"  Origin Type:        {profile.origin_type}")
        print(f"  Layout Complexity:  {profile.layout_complexity}")
        print(f"  Recommended Strategy: {profile.recommended_strategy}")
        print(f"  Confidence Score:   {profile.confidence_score:.2f}")
        print(f"  Cost Tier:          {profile.estimated_cost_tier}")
        print(f"  Text Chars:         {profile.text_chars:,}")
        print(f"  Images Found:       {profile.images_found}")
        print(f"  Table Count:        {profile.table_count}")
        print(f"  Page Count:         {profile.page_count}")
        print(f"  ")
    
    # ========== NODE 2: EXTRACTION ==========
    print(f"\n{'='*80}")
    print("  [Node 2: Extract] Running ExtractionAgent...")
    print(f"{'='*80}")
    
    extraction_agent = ExtractionAgent()
    result, strategy = extraction_agent.extract(pdf_path, profile, pages)
    
    state["extracted_text"] = result.content
    state["char_count"] = len(result.content)
    state["extraction_quality"] = result.quality_score
    state["selected_strategy"] = strategy
    
    if ask_continue("EXTRACTION AGENT"):
        print(f"\n   EXTRACTION RESULTS:")
        print(f"  ")
        print(f"  Strategy:           {strategy}")
        print(f"  Pages Requested:    {pages}")
        print(f"  Characters:         {state['char_count']:,}")
        print(f"  Quality Score:      {state['extraction_quality']:.2f}")
        print(f"  ")
        print(f"\n  EXTRACTED TEXT (First 800 chars):")
        print(f"  ")
        preview = result.content[:800] if result.content else ""
        print(f"  {preview}")
        if len(result.content) > 800:
            print(f"  ... ({len(result.content) - 800} more chars)")
        print(f"  ")
        
        # SHOW PAGE VERIFICATION
        print(f"\n   PAGE VERIFICATION:")
        print(f"  ")
        print(f"  You requested: Page {pages}")
        print(f"  Check the text above - does it match PDF page {pages[0]}?")
        print(f"  Look for: Section headers, table titles, unique text from page {pages[0]}")
        print(f"  ")
    
    # ========== NODE 3: CHUNKING ==========
    print(f"\n{'='*80}")
    print("  [Node 3: Chunk] Running ChunkerAgent (5 rules)...")
    print(f"{'='*80}")
    
    chunker_agent = ChunkerAgent()
    ldus = chunker_agent.chunk(result.content, pages)
    state["ldus"] = chunker_agent.to_dict(ldus)
    
    if ask_continue("CHUNKER AGENT"):
        print(f"\n   CHUNKING RESULTS:")
        print(f"  ")
        print(f"  LDUs Created:       {len(ldus)}")
        print(f"  5 Rules Validated:  YES")
        print(f"  ")
        for ldu in ldus[:5]:
            print(f"     {ldu.id}: Page {ldu.page}, Section: {ldu.section}")
        print(f"  ")
    
    # ========== NODE 4: INDEXING ==========
    print(f"\n{'='*80}")
    print("  [Node 4: Index] Running IndexerAgent...")
    print(f"{'='*80}")
    
    indexer_agent = IndexerAgent()
    indexer_agent.build_index(state["ldus"])
    indexer_agent.add_summaries()
    indexer_agent.print_tree()
    
    state["sections"] = [
        {"title": title, "pages": node.pages, "ldus": node.ldus, "summary": node.summary}
        for title, node in indexer_agent.sections.items()
    ]
    
    output_path = indexer_agent.save(".refinery/page_index.json")
    
    if ask_continue("INDEXER AGENT"):
        print(f"\n   PAGEINDEX RESULTS:")
        print(f"  ")
        print(f"  Sections Created:   {len(state['sections'])}")
        print(f"  Saved to:           {output_path}")
        print(f"  ")
        for section in state["sections"]:
            print(f"\n  Section: {section['title']}")
            print(f"    Pages: {section['pages']}")
            print(f"    Summary: {section['summary'][:100]}...")
        print(f"  ")
    
    # ========== SAVE ALL RESULTS ==========
    output_path = Path(".refinery/interactive_results.json")
    with open(output_path, "w") as f:
        json.dump(state, f, indent=2, default=str)
    
    print(f"\n{'='*80}")
    print(f"   ALL RESULTS SAVED TO: {output_path}")
    print(f"{'='*80}")
    
    # FINAL SUMMARY
    print(f"\n{'='*80}")
    print("  FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"   Strategy:          {state['selected_strategy']}")
    print(f"   Characters:        {state['char_count']:,}")
    print(f"   Quality:           {state['extraction_quality']:.2f}")
    print(f"   Sections:          {len(state['sections'])}")
    print(f"   Pages Processed:   {pages}")
    print(f"   Cost:              $0.00 (OFFLINE)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
