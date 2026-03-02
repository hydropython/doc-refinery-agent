import lancedb
import os
from pathlib import Path
from tabulate import tabulate

def debug_vault():
    # 1. Use an Absolute Path to avoid "missing table" errors
    base_path = Path("./.refinery_db").absolute()
    db_uri = str(base_path / "audit_lancedb")
    
    print(f"📂 Checking Database at: {db_uri}")
    
    if not os.path.exists(db_uri):
        print(f"❌ Error: The directory {db_uri} does not exist yet!")
        return

    db = lancedb.connect(db_uri)
    
    # 2. FIX: Parse the TableNames response object
    response = db.list_tables()
    print(f"📋 Tables found: {response}")

    # We check inside the .tables list specifically
    if "audit_telemetry" not in response.tables:
        print("❌ Error: 'audit_telemetry' not found in the tables list.")
        return

    table = db.open_table("audit_telemetry")

    # 3. Retrieve Data using Arrow-compliant pylist
    results = table.head(5).to_pylist()

    if not results:
        print("Empty Table: No rows found.")
        return

    # 4. Generate Production Report
    report_data = []
    for r in results:
        # Access nested metadata with fallback
        metadata = r.get('metadata', {})
        filename = metadata.get('filename', 'Unknown')
        chunk_size = metadata.get('chunk_size', len(r['text']))
        
        clean_text = r['text'].replace('\n', ' ')[:80]
        report_data.append([
            filename, 
            f"{clean_text}...", 
            f"{chunk_size} chars"
        ])

    print(f"\n📊 DATABASE SNAPSHOT (Total Rows: {len(table)})")
    print(tabulate(report_data, headers=["Source", "Content Preview", "Size"], tablefmt="grid"))

if __name__ == "__main__":
    debug_vault()