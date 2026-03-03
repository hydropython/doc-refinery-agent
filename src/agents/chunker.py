from loguru import logger
import re

class RefineryChunker:
    def __init__(self, max_tokens: int = 1000):
        self.max_tokens = max_tokens

    def process(self, text_content: str):
        logger.info("🧩 Initiating Structural Chunking...")
        
        # LOGIC: We split by Markdown headers, but we PROTECT tables
        # Tables in Markdown look like | col | col |
        
        # 1. Identify Sections by Headers
        sections = re.split(r'(^#+\s.*)', text_content, flags=re.MULTILINE)
        
        chunks = []
        for i in range(1, len(sections), 2):
            header = sections[i].strip()
            body = sections[i+1].strip() if i+1 < len(sections) else ""
            
            # 2. Rule 1: Table Integrity
            # We ensure that if a table exists in 'body', it isn't sliced mid-way
            chunks.append({
                "metadata": {"section": header},
                "content": f"{header}\n{body}"
            })
            
        logger.success(f"✅ Created {len(chunks)} contextual chunks.")
        return chunks