import sys
import os
from pathlib import Path
from loguru import logger
from tabulate import tabulate

# 🧪 CALLING RESEARCH LOGIC
try:
    from research.density_profiler import analyze_document_physics as run_physics_analysis
    from research.quality_checker import calculate_ocr_quality
    from research.benchmark_docling import run_docling_test as run_docling_extraction
except ImportError as e:
    logger.error(f"❌ Module Import Error: {e}")
    sys.exit(1)

# 🏗️ INFRASTRUCTURE
from src.agents.triage import analyze_document
from src.indexer.chroma_indexer import ChromaIndexer


class DocRefineryAgent:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent
        self.data_dir = self.base_dir / "data"
        self.output_root = self.base_dir / "output" / "refined"
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.indexer = ChromaIndexer()
        self.summary_data = []

    def get_all_chunks(self):
        """Helper to collect every PDF across all chunk_ folders"""
        all_files = []
        silos = sorted([d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith("chunk_")])
        for silo in silos:
            all_files.extend(list(silo.glob("*.pdf")))
        return all_files

    def select_mode(self):
        """Tier 1: Mode Selection (Silo vs Global Loop)"""
        silos = sorted([d for d in self.data_dir.iterdir() if d.is_dir() and d.name.startswith("chunk_")])
        
        print("\n🏢 INSTITUTIONAL SILO SELECTION:")
        print("[A] PROCESS ALL SILOS (Global Loop)")
        for idx, silo in enumerate(silos):
            print(f"[{idx}] {silo.name}")
        
        choice = input("\n👉 Select Institution Index or 'A' for ALL: ").strip().upper()
        
        if choice == 'A':
            logger.info("🌍 MODE: Processing ALL silos in global loop")
            return self.get_all_chunks()
        
        try:
            selected_silo = silos[int(choice)]
            files = sorted(list(selected_silo.glob("*.pdf")))
            logger.info(f"📂 MODE: Processing all files in {selected_silo.name}")
            return files  # Return ALL files in selected silo
        except (ValueError, IndexError) as e:
            logger.error(f"❌ Invalid selection: {e}")
            return None

    def process(self, target_files):
        """The Global Ingestion Loop - Process ALL files in one loop"""
        
        total_files = len(target_files)
        logger.info(f"🚀 Starting global loop: {total_files} files to process")
        print("=" * 80)
        
        for idx, pdf in enumerate(target_files, 1):
            print(f"\n[{idx}/{total_files}] Processing: {pdf.name}")
            print("-" * 80)
            
            # Create institutional output folder (e.g., chunk_cbe -> refined_cbe)
            silo_folder_name = pdf.parent.name.replace("chunk_", "refined_")
            silo_output_path = self.output_root / silo_folder_name
            silo_output_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"--- 💠 REFINING: {pdf.name} -> {silo_folder_name} 💠 ---")
            
            try:
                # Step 1: Physics Analysis (pdfplumber metrics + CSV save)
                logger.info("Step 1: Running Document Density Profiling...")
                physics_metrics = run_physics_analysis(folder_path=str(pdf.resolve()))
                
                # Step 2: Triage
                logger.info("Step 2: Running Triage Agent...")
                triage_result = analyze_document(str(pdf.resolve()))
                logger.success(f"Triage Complete: {triage_result.origin_type} | {triage_result.layout_complexity}")

                # Step 3: Extraction (Docling)
                logger.info("Step 3: Running Docling Structural Recovery...")
                print(f"🚀 Docling is processing: {pdf.name}...")
                markdown_content = run_docling_extraction(file_name=pdf.name)
                
                if not markdown_content:
                    logger.warning(f"⚠️  Extraction failed for {pdf.name}")
                    self.summary_data.append([
                        pdf.name,
                        silo_folder_name,
                        "N/A",
                        "❌ EXTRACTION FAILED"
                    ])
                    continue

                # Save refined markdown
                output_filename = f"refined_{pdf.stem}.md"
                output_path = silo_output_path / output_filename
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                logger.info(f"✅ Refined Markdown saved to: {output_path}")

                # Step 4: Quality Gate
                logger.info("Step 4: Running Quality Gate...")
                metrics = calculate_ocr_quality(text=markdown_content)
                score = metrics['quality_score']
                logger.info(f"Quality Score: {score:.2f}")
                
                # Step 5: Indexing
                status = "❌ REJECTED"
                if score >= 0.75:
                    self.indexer.index_document(str(pdf.resolve()), markdown_content)
                    status = "✅ INDEXED"
                
                # Add to summary with strategy info
                strategy = physics_metrics.get('recommended_strategy', 'Unknown') if isinstance(physics_metrics, dict) else 'Unknown'
                self.summary_data.append([
                    pdf.name,
                    silo_folder_name,
                    f"{score:.2f}",
                    f"{status} | {strategy}"
                ])
                
                print(f"✅ [{idx}/{total_files}] Complete: {pdf.name} | Score: {score:.2f} | {status}")
                
            except Exception as e:
                logger.error(f"❌ Error processing {pdf.name}: {e}")
                self.summary_data.append([
                    pdf.name,
                    silo_folder_name,
                    "ERROR",
                    f"❌ {str(e)}"
                ])
        
        print("\n" + "=" * 80)
        self.display_summary()

    def display_summary(self):
        """Display final processing summary"""
        headers = ["Segment", "Silo", "QA Score", "Final Status"]
        print("\n📊 PHASE 0 & 1 INTEGRATION SUMMARY")
        print(tabulate(self.summary_data, headers=headers, tablefmt="grid"))
        
        # Save summary to CSV
        summary_path = self.base_dir / ".refinery" / "processing_summary.csv"
        summary_path.parent.mkdir(exist_ok=True)
        
        import csv
        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(self.summary_data)
        
        print(f"\n📁 Summary saved to: {summary_path}")
        
        # Print statistics
        total = len(self.summary_data)
        indexed = sum(1 for row in self.summary_data if "✅ INDEXED" in row[3])
        failed = total - indexed
        
        print(f"\n📈 STATISTICS:")
        print(f"   Total Files: {total}")
        print(f"   ✅ Indexed: {indexed} ({indexed/total*100:.1f}%)")
        print(f"   ❌ Failed: {failed} ({failed/total*100:.1f}%)")


# ============================================================================
# 🚀 ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    logger.add(".refinery/pipeline.log", rotation="10 MB", retention="7 days")
    
    agent = DocRefineryAgent()
    selected = agent.select_mode()
    
    if selected:
        agent.process(selected)
    else:
        logger.error("❌ No files selected. Exiting.")