import pdfplumber
from src.models.schemas import ExtractedDocument, Table

class FastTextExtractor:
    def extract(self, pdf_path: str) -> ExtractedDocument:
        full_text = []
        extracted_tables = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                full_text.append(page.extract_text() or "")
                # Basic table extraction
                page_tables = page.extract_tables()
                for tbl in page_tables:
                    if tbl:
                        extracted_tables.append(Table(
                            headers=[str(c) for c in tbl[0]],
                            rows=tbl[1:],
                            page_ref=i + 1
                        ))
                        
        return ExtractedDocument(
            doc_id=pdf_path.split("/")[-1],
            text_content="\n".join(full_text),
            tables=extracted_tables,
            strategy_used="fast_text",
            confidence_score=0.9
        )