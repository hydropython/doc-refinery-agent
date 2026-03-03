import os
from pathlib import Path
from docling.document_converter import DocumentConverter

def run_docling_test(file_name):
    # 1. Setup Base Paths
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    
    # 2. Find Source and Determine Institutional Silo
    source_path = None
    silo_name = None
    
    for silo in data_dir.glob("chunk_*"):
        potential_file = silo / file_name
        if potential_file.exists():
            source_path = potential_file
            # Map chunk_audit -> REFINED_AUDIT
            silo_name = silo.name.upper().replace("CHUNK_", "REFINED_")
            break

    if not source_path:
        return None

    # 3. Setup Dedicated Refined Folder
    refined_output_dir = base_dir / "output" / "refined" / silo_name
    refined_output_dir.mkdir(parents=True, exist_ok=True)

    # 4. Conversion Logic
    converter = DocumentConverter()
    result = converter.convert(str(source_path.resolve()))
    markdown_output = result.document.export_to_markdown()

    # 5. Save into REFINED_{INSTITUTION}
    save_path = refined_output_dir / f"refined_{file_name.replace('.pdf', '.md')}"
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(markdown_output)

    return markdown_output