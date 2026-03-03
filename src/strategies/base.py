from abc import ABC, abstractmethod
from src.models.schemas import ExtractedDocument

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, pdf_path: str) -> ExtractedDocument:
        """Standard method for all extraction strategies"""
        pass