from pypdf import PdfReader, PdfWriter
import os

def split_pdf(input_path, chunk_size=10):
    reader = PdfReader(input_path)
    # FIX: Use .pages to get the length
    total_pages = len(reader.pages) 
    
    output_dir = "data/chunks"
    os.makedirs(output_dir, exist_ok=True)

    for i in range(0, total_pages, chunk_size):
        writer = PdfWriter()
        # Slice the pages correctly
        for page_num in range(i, min(i + chunk_size, total_pages)):
            writer.add_page(reader.pages[page_num])
        
        output_filename = f"{output_dir}/audit_part_{i//chunk_size + 1}.pdf"
        with open(output_filename, "wb") as f:
            writer.write(f)
        print(f"✅ Created: {output_filename} (Pages {i} to {min(i + chunk_size, total_pages)})")

if __name__ == "__main__":
    split_pdf("data/Audit Report - 2023.pdf")