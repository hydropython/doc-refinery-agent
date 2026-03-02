import pdfplumber
from rapidocr_onnxruntime import RapidOCR
from loguru import logger
import numpy as np
from PIL import Image

class LayoutAwareExtractor:
    def __init__(self):
        self.ocr = RapidOCR()

    def extract(self, file_path: str):
        logger.info(f"🔍 Analyzing Layout & Performing OCR for {file_path}")
        full_output = []

        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # 1. Check for digital text first
                text = page.extract_text()
                
                if text and len(text.strip()) > 50:
                    full_output.append(text)
                else:
                    # 2. If no text, trigger RapidOCR (Scanned Page)
                    logger.info(f"📸 Page {i+1} appears to be a scan. Triggering OCR...")
                    img = page.to_image(resolution=300).original
                    # Convert PIL to OpenCv/Numpy format for RapidOCR
                    result, _ = self.ocr(np.array(img))
                    
                    if result:
                        page_text = "\n".join([line[1] for line in result])
                        full_output.append(page_text)

        return "\n\n".join(full_output)