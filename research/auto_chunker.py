import os
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path

def split_to_named_folder(file_path, folder_name, chunk_size=10):
    if not os.path.exists(file_path):
        print(f"⚠️ Skip: {file_path} not found.")
        return

    reader = PdfReader(file_path)
    output_dir = Path(f"data/{folder_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(file_path).stem.replace(" ", "_").lower()

    for i in range(0, len(reader.pages), chunk_size):
        writer = PdfWriter()
        for page in reader.pages[i : i + chunk_size]:
            writer.add_page(page)
        
        chunk_path = output_dir / f"{base_name}_pt_{i//chunk_size + 1}.pdf"
        with open(chunk_path, "wb") as f:
            writer.write(f)
    print(f"✅ Created {folder_name} with segments from {base_name}.")

if __name__ == "__main__":
    # Mapping your files to your requested folder names
    jobs = [
        ("data/Audit Report - 2023.pdf", "chunk_audit"),
        ("data/CBE ANNUAL REPORT 2023-24.pdf", "chunk_cbe"),
        ("data/fta_performance_survey_final_report_2022.pdf", "chunk_fta"),
        ("data/tax_expenditure_ethiopia_2021_22.pdf", "chunk_tax")
    ]
    
    for file, folder in jobs:
        split_to_named_folder(file, folder)