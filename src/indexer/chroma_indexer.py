import lancedb
from pathlib import Path
from loguru import logger
import uuid

class ChromaIndexer:
    def __init__(self, persist_directory="./.refinery_db"):
        self.db_path = Path(persist_directory)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Connect to the persistent storage
        self.uri = str(self.db_path / "audit_lancedb")
        self.db = lancedb.connect(self.uri)
        self.table_name = "audit_telemetry"

    def index_document(self, file_path, text_content):
        """
        Handles the hand-off from OCR to Database.
        """
        # --- TYPE SAFETY LAYER ---
        # If the extractor returned a TableData object (Docling) or similar
        if not isinstance(text_content, str):
            logger.info(f"🔄 Normalizing {type(text_content).__name__} for {Path(file_path).name}")
            try:
                # Try to get markdown if it's a structural object
                text_content = text_content.export_to_markdown()
            except:
                # Fallback to standard string
                text_content = str(text_content)

        # 1. Production Chunking
        # We split by double newline to keep paragraphs together
        chunks = [c.strip() for c in text_content.split("\n\n") if len(c.strip()) > 60]
        
        if not chunks:
            logger.warning(f"⚠️ No indexable text found in {file_path}")
            return

        # 2. Schema Preparation
        payload = [
            {
                "id": str(uuid.uuid4()),
                "text": chunk,
                "metadata": {
                    "source": str(file_path),
                    "filename": Path(file_path).name,
                    "char_count": len(chunk)
                }
            }
            for chunk in chunks
        ]

        # 3. Commit to LanceDB
        if self.table_name in self.db.table_names():
            table = self.db.open_table(self.table_name)
            table.add(payload)
        else:
            self.db.create_table(self.table_name, data=payload)
            
        logger.success(f"🔒 Database Updated: {len(chunks)} chunks committed.")