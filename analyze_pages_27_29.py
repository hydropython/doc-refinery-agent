"""
Document Analysis - Count Images & Tables on Pages 27-29
Location: analyze_pages_27_29.py
"""

import fitz
import json
from pathlib import Path

pdf_path = "data/fta_performance_survey_final_report_2022.pdf"
pages_to_analyze = [27, 28, 29]

print("\n" + "="*80)
print("  DOCUMENT ANALYSIS - Pages 27-29")
print("="*80)
print(f"  Document: {pdf_path}")
print(f"  Pages to Analyze: {pages_to_analyze}")
print("="*80)

pdf = fitz.open(pdf_path)

results = []

for sys_page_num in pages_to_analyze:
    if sys_page_num <= len(pdf):
        page = pdf[sys_page_num - 1]  # 0-indexed
        page_num = sys_page_num
        
        # Get page info
        text = page.get_text()
        images = page.get_images(full=True)
        tables = page.find_tables()
        drawings = page.get_drawings()
        
        # Try to find printed page number
        lines = text.strip().split('\n')
        printed_page = "N/A"
        for line in lines[-3:]:
            line = line.strip()
            if line.isdigit():
                printed_page = line
                break
        
        result = {
            "system_page": sys_page_num,
            "printed_page": printed_page,
            "char_count": len(text),
            "image_count": len(images),
            "table_count": len(tables.tables),
            "drawing_count": len(drawings),
            "text_preview": text[:500].replace('\n', ' ')
        }
        results.append(result)
        
        print(f"\n{'='*80}")
        print(f"  PAGE {sys_page_num} (Printed: {printed_page})")
        print(f"{'='*80}")
        print(f"  Characters:     {len(text):,}")
        print(f"  Images:         {len(images)}")
        print(f"  Tables:         {len(tables.tables)}")
        print(f"  Drawings:       {len(drawings)}")
        print(f"\n  Text Preview (First 500 chars):")
        print(f"  {'-'*76}")
        print(f"  {text[:500]}")
        print(f"  {'-'*76}")
        
        # Show image details
        if images:
            print(f"\n  IMAGES FOUND ({len(images)}):")
            for i, img in enumerate(images[:5], 1):
                print(f"    Image {i}: {img}")
            if len(images) > 5:
                print(f"    ... and {len(images) - 5} more")
        
        # Show table details
        if tables.tables:
            print(f"\n  TABLES FOUND ({len(tables.tables)}):")
            for i, table in enumerate(tables.tables[:3], 1):
                print(f"    Table {i}:")
                print(f"      BBox: {table.bbox}")
                print(f"      Rows: {table.row_count}, Cols: {table.col_count}")
                # Show first few cells
                try:
                    data = table.extract()
                    if data:
                        print(f"      First row: {data[0]}")
                except:
                    pass
            if len(tables.tables) > 3:
                print(f"    ... and {len(tables.tables) - 3} more")

pdf.close()

# Save summary
output_path = Path(".refinery/page_analysis_27_29.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w") as f:
    json.dump(results, f, indent=2, default=str)

print(f"\n{'='*80}")
print(f"  SUMMARY SAVED TO: {output_path}")
print(f"{'='*80}")

# Overall summary
print(f"\n{'='*80}")
print(f"  OVERALL SUMMARY (Pages 27-29)")
print(f"{'='*80}")
total_images = sum(r["image_count"] for r in results)
total_tables = sum(r["table_count"] for r in results)
total_chars = sum(r["char_count"] for r in results)
print(f"  Total Images:   {total_images}")
print(f"  Total Tables:   {total_tables}")
print(f"  Total Chars:    {total_chars:,}")
print(f"{'='*80}\n")

print("  INSTRUCTIONS:")
print("  1. Open PDF and go to pages 27-29 (check printed page numbers above)")
print("  2. Verify: Do you see the same number of images/tables?")
print("  3. For each table, write down the ACTUAL values (ground truth)")
print("  4. Share with me for verification report\n")
